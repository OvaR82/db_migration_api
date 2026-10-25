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
# Configuración
# ----------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
MAP_FILE = os.path.join(CONFIG_DIR, "header_mappings.yaml")
SET_FILE = os.path.join(CONFIG_DIR, "settings.yaml")

# Único directorio desde el que se permite leer CSV con `source_path`.
DATA_DIR = os.path.realpath(os.getenv("INGEST_DATA_DIR", os.path.join(BASE_DIR, "data")))

MODELS = {"departments": Department, "jobs": Job, "employees": Employee}
MODES = ("insert", "ignore", "update")

# Máximo de filas rechazadas que se devuelven en la respuesta (todas se loguean).
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
        raise ValueError(f"settings.yaml: ingest.upsert inválido '{mode}'. Use {MODES}.")
    return mode


# ----------------------------
# Lectura de archivos locales
# ----------------------------
def read_source_file(source_path: str) -> str:
    """Lee un CSV dentro de DATA_DIR. Rechaza rutas fuera de ese directorio."""
    full = os.path.realpath(os.path.join(DATA_DIR, source_path))
    if os.path.commonpath([full, DATA_DIR]) != DATA_DIR:
        raise ValueError("source_path debe estar dentro del directorio de datos.")
    if not os.path.isfile(full):
        raise ValueError(f"Archivo no encontrado: {source_path}")
    with open(full, "r", encoding="utf-8-sig") as f:
        return f.read()


# ----------------------------
# Normalización de headers
# ----------------------------
def _clean_header(h: str) -> str:
    # Quita BOM, espacios y baja a minúsculas
    return h.replace("﻿", "").strip().lower()


def _normalize_headers(headers: List[str], table: TableName) -> Dict[str, str]:
    """Devuelve {header_original: columna_estándar}. Falla si falta alguna columna."""
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
            raise ValueError(f"Varias columnas del CSV corresponden a '{std}' en {table}. Got: {headers}")
        mapping[h] = std

    missing = [c for c in expected if c not in mapping.values()]
    if missing:
        raise ValueError(f"CSV headers missing {missing} for {table}. Got: {headers}")
    return mapping


# ----------------------------
# Validación por fila
# ----------------------------
def _required_int(value, field: str) -> int:
    if value is None or str(value).strip() in ("", "NULL", "null"):
        raise ValueError(f"{field} vacío o nulo")
    return int(value)


def _required_str(value, field: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field} vacío")
    return str(value).strip()


def _coerce_row(table: TableName, row: Dict[str, str]) -> Dict[str, object]:
    if table == "departments":
        return {"id": _required_int(row.get("id"), "id"), "name": _required_str(row.get("name"), "name")}
    if table == "jobs":
        return {"id": _required_int(row.get("id"), "id"), "title": _required_str(row.get("title"), "title")}
    if table == "employees":
        hd = row.get("hire_date")
        if hd is None or not str(hd).strip():
            raise ValueError("hire_date vacía o nula")
        return {
            "id": _required_int(row.get("id"), "id"),
            "name": _required_str(row.get("name"), "name"),
            "department_id": _required_int(row.get("department_id"), "department_id"),
            "job_id": _required_int(row.get("job_id"), "job_id"),
            # La columna es DATE: se guarda la fecha en UTC.
            "hire_date": parse_date(hd).astimezone(timezone.utc).date(),
        }
    raise ValueError(f"Tabla no soportada: {table}")


# ----------------------------
# Escritura en BD
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
            raise ValueError(f"Modo '{mode}' no soportado para el dialecto {dialect}.")
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
    """COPY a una tabla temporal y luego INSERT ... SELECT (psycopg 3)."""
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
# Ingesta principal
# ----------------------------
def ingest_csv(
    db: Session,
    table: TableName,
    content: str,
    skip_invalid_rows: bool = False,
    mode: str | None = None,
) -> dict:
    """
    Ingesta transaccional desde CSV (todo o nada).
    - skip_invalid_rows=True: omite filas inválidas y las informa en `errors`.
    - mode: "insert" | "ignore" | "update". Por defecto, `ingest.upsert` de settings.yaml.
    """
    mode = mode or default_mode()
    if mode not in MODES:
        raise ValueError(f"mode inválido '{mode}'. Use {MODES}.")

    reader = csv.reader(io.StringIO(content))
    headers = next(reader, None)
    if not headers:
        raise ValueError("CSV vacío o sin encabezados.")
    header_map = _normalize_headers(headers, table)

    rows: List[Dict[str, object]] = []
    errors: List[Dict[str, object]] = []
    for line_no, values in enumerate(reader, start=2):  # la línea 1 es el header
        if not any(v.strip() for v in values):
            continue  # línea vacía
        raw = {header_map[h]: v for h, v in zip(headers, values) if h in header_map}
        try:
            rows.append(_coerce_row(table, raw))
        except ValueError as e:
            if not skip_invalid_rows:
                raise ValueError(f"Error en fila {line_no}: {e}") from e
            errors.append({"row": line_no, "error": str(e)})
            logger.warning("ingest %s: fila %d omitida: %s", table, line_no, e)

    if rows:
        with db.begin():
            _write_rows(db, table, rows, mode)

    return {
        "mode": mode,
        "inserted": len(rows),
        "skipped": len(errors),
        "errors": errors[:MAX_REPORTED_ERRORS],
    }
