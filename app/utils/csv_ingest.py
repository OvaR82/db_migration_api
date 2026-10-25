import csv
import io
import logging
import os
from copy import deepcopy
from datetime import timezone
from typing import Dict, List

import yaml
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from ..models import Department, Employee, Job
from .types import EXPECTED_HEADERS, TableName
from .validators import parse_date

logger = logging.getLogger(__name__)

# ----------------------------
# Configuration
# ----------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
MAP_FILE = os.path.join(CONFIG_DIR, "header_mappings.yaml")
SET_FILE = os.path.join(CONFIG_DIR, "settings.yaml")

# Only directory `source_path` is allowed to read CSV files from.
DATA_DIR = os.path.realpath(os.getenv("INGEST_DATA_DIR", os.path.join(BASE_DIR, "data")))

MODELS = {"departments": Department, "jobs": Job, "employees": Employee}
MODES = ("insert", "ignore", "update")

# Max rejected rows returned in the response (all of them are logged).
MAX_REPORTED_ERRORS = 100


def _load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


DEFAULT_SETTINGS = {
    "ingest": {
        "use_copy_for_postgres": False,
        "upsert": "insert",  # "insert" | "ignore" | "update"
    }
}
HEADER_MAPS = _load_yaml(MAP_FILE)
SETTINGS = _deep_merge(DEFAULT_SETTINGS, _load_yaml(SET_FILE))


def default_mode() -> str:
    mode = SETTINGS["ingest"].get("upsert") or "insert"
    if mode not in MODES:
        raise ValueError(f"settings.yaml: invalid ingest.upsert '{mode}'. Use {MODES}.")
    return mode


# ----------------------------
# Local file reading
# ----------------------------
def read_source_file(source_path: str) -> str:
    """Read a CSV inside DATA_DIR. Rejects paths outside that directory."""
    full = os.path.realpath(os.path.join(DATA_DIR, source_path))
    if os.path.commonpath([full, DATA_DIR]) != DATA_DIR:
        raise ValueError("source_path must be inside the data directory.")
    if not os.path.isfile(full):
        raise ValueError(f"File not found: {source_path}")
    with open(full, "r", encoding="utf-8-sig") as f:
        return f.read()


# ----------------------------
# Header normalization
# ----------------------------
def _clean_header(h: str) -> str:
    # Strip BOM and spaces, lowercase
    return h.replace("\ufeff", "").strip().lower()


def _normalize_headers(headers: List[str], table: TableName) -> Dict[str, str]:
    """Return {original_header: standard_column}. Fails if a column is missing."""
    expected = EXPECTED_HEADERS[table]

    alias_to_std = {}
    for std, alias_list in (HEADER_MAPS.get(table) or {}).items():
        for alias in alias_list:
            alias_to_std[_clean_header(alias)] = std
    for std in expected:
        alias_to_std.setdefault(std.lower(), std)

    mapping: Dict[str, str] = {}
    for h in headers:
        std = alias_to_std.get(_clean_header(h))
        if not std:
            continue
        if std in mapping.values():
            raise ValueError(f"Several CSV columns map to '{std}' in {table}. Got: {headers}")
        mapping[h] = std

    missing = [c for c in expected if c not in mapping.values()]
    if missing:
        raise ValueError(f"CSV headers missing {missing} for {table}. Got: {headers}")
    return mapping


# ----------------------------
# Per-row validation
# ----------------------------
def _required_int(value, field: str) -> int:
    if value is None or str(value).strip() in ("", "NULL", "null"):
        raise ValueError(f"{field} is empty or null")
    return int(value)


def _required_str(value, field: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field} is empty")
    return str(value).strip()


def _coerce_row(table: TableName, row: Dict[str, str]) -> Dict[str, object]:
    if table == "departments":
        return {"id": _required_int(row.get("id"), "id"), "name": _required_str(row.get("name"), "name")}
    if table == "jobs":
        return {"id": _required_int(row.get("id"), "id"), "title": _required_str(row.get("title"), "title")}
    if table == "employees":
        hd = row.get("hire_date")
        if hd is None or not str(hd).strip():
            raise ValueError("hire_date is empty or null")
        return {
            "id": _required_int(row.get("id"), "id"),
            "name": _required_str(row.get("name"), "name"),
            "department_id": _required_int(row.get("department_id"), "department_id"),
            "job_id": _required_int(row.get("job_id"), "job_id"),
            # The column is DATE: store the UTC date.
            "hire_date": parse_date(hd).astimezone(timezone.utc).date(),
        }
    raise ValueError(f"Tabla no soportada: {table}")


# ----------------------------
# Database writes
# ----------------------------
def _write_rows(db: Session, table: TableName, rows: List[Dict[str, object]], mode: str) -> None:
    model = MODELS[table]
    cols = EXPECTED_HEADERS[table]
    dialect = db.bind.dialect.name

    if dialect.startswith("postgresql") and SETTINGS["ingest"].get("use_copy_for_postgres"):
        _copy_postgres(db, table, cols, rows, mode)
        return

    if dialect.startswith("postgresql"):
        stmt = postgresql.insert(model.__table__)
    elif dialect.startswith("sqlite"):
        stmt = sqlite.insert(model.__table__)
    else:
        if mode != "insert":
            raise ValueError(f"Mode '{mode}' is not supported for dialect {dialect}.")
        db.execute(model.__table__.insert(), rows)
        return

    if mode == "ignore":
        stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
    elif mode == "update":
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={c: stmt.excluded[c] for c in cols if c != "id"},
        )
    db.execute(stmt, rows)


def _copy_postgres(db: Session, table: TableName, cols: List[str], rows, mode: str) -> None:
    """COPY into a temp table, then INSERT ... SELECT (psycopg 3)."""
    col_list = ", ".join(cols)
    conflict = ""
    if mode == "ignore":
        conflict = "ON CONFLICT (id) DO NOTHING"
    elif mode == "update":
        conflict = "ON CONFLICT (id) DO UPDATE SET " + ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "id")

    raw = db.connection().connection.driver_connection
    with raw.cursor() as cur:
        cur.execute(f"CREATE TEMP TABLE staging_{table} (LIKE {table}) ON COMMIT DROP")
        with cur.copy(f"COPY staging_{table} ({col_list}) FROM STDIN") as cp:
            for r in rows:
                cp.write_row([r[c] for c in cols])
        cur.execute(f"INSERT INTO {table} ({col_list}) SELECT {col_list} FROM staging_{table} {conflict}")


# ----------------------------
# Main ingestion
# ----------------------------
def ingest_csv(
    db: Session,
    table: TableName,
    content: str,
    skip_invalid_rows: bool = False,
    mode: str | None = None,
) -> dict:
    """
    Transactional CSV ingestion (all or nothing).
    - skip_invalid_rows=True: skip invalid rows and report them in `errors`.
    - mode: "insert" | "ignore" | "update". Defaults to `ingest.upsert` in settings.yaml.
    """
    mode = mode or default_mode()
    if mode not in MODES:
        raise ValueError(f"Invalid mode '{mode}'. Use {MODES}.")

    reader = csv.reader(io.StringIO(content))
    headers = next(reader, None)
    if not headers:
        raise ValueError("Empty CSV or missing header row.")
    header_map = _normalize_headers(headers, table)

    rows: List[Dict[str, object]] = []
    errors: List[Dict[str, object]] = []
    for line_no, values in enumerate(reader, start=2):  # line 1 is the header
        if not any(v.strip() for v in values):
            continue  # blank line
        raw = {header_map[h]: v for h, v in zip(headers, values) if h in header_map}
        try:
            rows.append(_coerce_row(table, raw))
        except ValueError as e:
            if not skip_invalid_rows:
                raise ValueError(f"Error in row {line_no}: {e}") from e
            errors.append({"row": line_no, "error": str(e)})
            logger.warning("ingest %s: skipped row %d: %s", table, line_no, e)

    if rows:
        with db.begin():
            _write_rows(db, table, rows, mode)

    return {
        "mode": mode,
        "inserted": len(rows),
        "skipped": len(errors),
        "errors": errors[:MAX_REPORTED_ERRORS],
    }
