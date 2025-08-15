import csv
from datetime import timezone
import io
import os
from typing import Dict, List

import requests
import yaml
from sqlalchemy import text
from sqlalchemy.orm import Session

from .types import TableName, EXPECTED_HEADERS
from .validators import parse_date, parse_decimal

# ----------------------------
# Configuration
# ----------------------------
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "config")
MAP_FILE = os.path.abspath(os.path.join(CONFIG_DIR, "header_mappings.yaml"))
SET_FILE = os.path.abspath(os.path.join(CONFIG_DIR, "settings.yaml"))

def _load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

# Safe defaults if YAML files are missing
HEADER_MAPS = _load_yaml(MAP_FILE)
SETTINGS = {
    "ingest": {
        "use_copy_for_postgres": True,
        "fail_fast_on_header_mismatch": False,
        "upsert": ""  # "", "ignore", "update"
    }
}
SETTINGS.update(_load_yaml(SET_FILE) or {})

# ----------------------------
# IO Utilities
# ----------------------------
def _open_source(source: str) -> io.StringIO:
    if source.startswith(("http://", "https://")):
        r = requests.get(source, timeout=30)
        r.raise_for_status()
        return io.StringIO(r.text)
    if os.path.isfile(source):
        with open(source, "r", encoding="utf-8") as f:
            return io.StringIO(f.read())
    # Direct content
    return io.StringIO(source)

def _clean_header(h: str) -> str:
    # Remove BOM, strip spaces, and lowercase
    return h.replace("\ufeff", "").strip().lower()

# ----------------------------
# Header normalization
# ----------------------------
def _normalize_headers(headers: List[str], table: TableName) -> Dict[str, str]:
    expected = EXPECTED_HEADERS[table]

    # alias -> standard (from YAML)
    aliases = HEADER_MAPS.get(table, {}) if isinstance(HEADER_MAPS, dict) else {}
    alias_to_std = {}
    for std, alias_list in aliases.items():
        for alias in alias_list:
            alias_to_std[_clean_header(alias)] = std

    # Build mapping from actual headers
    mapping: Dict[str, str] = {}
    expected_lower = [c.lower() for c in expected]

    for h in headers:
        ch = _clean_header(h)
        std = alias_to_std.get(ch)
        if std:
            mapping[h] = std
        elif ch in expected_lower:
            std2 = expected[expected_lower.index(ch)]
            mapping[h] = std2

    missing = [c for c in expected if c not in mapping.values()]
    if missing:
        if SETTINGS.get("ingest", {}).get("fail_fast_on_header_mismatch", True):
            raise ValueError(f"CSV headers missing {missing} for {table}. Got: {headers}")
    return mapping

# ----------------------------
# Type coercion by table
# ----------------------------
def _coerce_row(table: TableName, row: Dict[str, str]) -> Dict[str, object]:
    try:
        if table in ("departments", "jobs"):
            row["id"] = int(row["id"])
            return row

        if table == "employees":
            row["id"] = int(row["id"])
            row["department_id"] = int(row["department_id"]) if row.get("department_id") not in (None, "",) else None
            row["job_id"] = int(row["job_id"]) if row.get("job_id") not in (None, "",) else None
            row["hire_date"] = parse_date(row["hire_date"])
            # 'name' is already a string
            return row

        return row
    except KeyError as e:
        missing = str(e).strip("'")
        raise ValueError(f"CSV missing required column '{missing}' for table '{table}'")

# ----------------------------
# UPSERT helpers
# ----------------------------
def _conflict_target(table: TableName) -> str:
    # Use PK 'id' as conflict target
    return "id"

def _update_set_clause(table: TableName) -> str:
    cols = [c for c in EXPECTED_HEADERS[table] if c != "id"]
    return ", ".join([f"{c}=excluded.{c}" for c in cols])

def _build_upsert_sql(dialect: str, table: TableName, mode: str) -> str:
    cols = EXPECTED_HEADERS[table]
    placeholders = ",".join([f":{c}" for c in cols])
    col_list = ",".join(cols)
    target = _conflict_target(table)

    if dialect.startswith("sqlite"):
        if mode == "ignore":
            return f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT({target}) DO NOTHING"
        if mode == "update":
            return f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT({target}) DO UPDATE SET {_update_set_clause(table)}"
        return f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    if dialect.startswith("postgresql"):
        if mode == "ignore":
            return f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT({target}) DO NOTHING"
        if mode == "update":
            return f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT({target}) DO UPDATE SET {_update_set_clause(table)}"
        return f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    # Other dialects
    return f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

# ----------------------------
# Main ingestion logic
# ----------------------------
def ingest_csv(db: Session, table: TableName, content: str, skip_invalid_rows: bool = False, mode: str = "insert"):
    """
    Transactional ingestion from CSV.
    - skip_invalid_rows=True: skip rows with invalid FKs/dates and count them.
    - mode: "insert" (default) or "upsert".
      * Postgres: upsert = COPY -> staging temp -> INSERT ... ON CONFLICT DO UPDATE
      * SQLite:   upsert = INSERT ... ON CONFLICT(id) DO UPDATE
    """
    dialect = db.bind.dialect.name
    sio = io.StringIO(content)
    reader = csv.reader(sio)
    headers = next(reader, None)
    if not headers:
        raise ValueError("CSV is empty or missing headers.")

    header_map = _normalize_headers(headers, table)

    # 1) Parsing + coercion + skipped row count
    sio.seek(0)
    dict_reader = csv.DictReader(sio)
    normalized_rows: List[Dict[str, object]] = []
    errors = 0

    required = EXPECTED_HEADERS[table]

    for idx, r in enumerate(dict_reader, start=2):  # start=2 because of header
        try:
            norm = {header_map.get(k, k): v for k, v in r.items()}
            norm = {k: v for k, v in norm.items() if k in required}

            # Table-specific coercion
            if table in ("departments", "jobs"):
                norm["id"] = int(norm["id"])
            elif table == "employees":
                # Validate FKs
                dep = norm.get("department_id")
                job = norm.get("job_id")
                if dep in (None, "", "NULL", "null"): raise ValueError("department_id is empty or null")
                if job in (None, "", "NULL", "null"): raise ValueError("job_id is empty or null")
                norm["department_id"] = int(dep)
                norm["job_id"] = int(job)

                # name
                name = norm.get("name", "")
                if not name or not name.strip(): raise ValueError("name is empty")
                norm["name"] = name.strip()

                # id
                norm["id"] = int(norm["id"])

                # hire_date
                hd = norm.get("hire_date")
                if hd is None or str(hd).strip() == "":
                    raise ValueError("hire_date is empty or null.")
                norm["hire_date"] = parse_date(hd)  # datetime aware
            else:
                raise ValueError(f"Unsupported table: {table}")

            normalized_rows.append(norm)

        except Exception as e:
            if skip_invalid_rows:
                errors += 1
                continue
            raise ValueError(f"Error in row {idx}: {e}") from e

    if not normalized_rows:
        # Nothing to insert
        return {"inserted": 0, "skipped": errors}

    # 2) INSERT / UPSERT by dialect
    if dialect.startswith("postgresql"):
        if mode == "insert":
            # === Direct COPY to target table ===
            # If any rows have NULLs in NOT NULL columns, COPY would fail.
            # Filter them out if skip_invalid_rows=True
            def row_ok(r: Dict[str, object]) -> bool:
                return all(r.get(col) is not None for col in required)

            if skip_invalid_rows:
                valid_rows = [r for r in normalized_rows if row_ok(r)]
                skipped_by_nulls = len(normalized_rows) - len(valid_rows)
                errors += skipped_by_nulls
            else:
                # Strict validation
                bad_idx = [i for i, r in enumerate(normalized_rows) if not row_ok(r)]
                if bad_idx:
                    raise ValueError(f"{len(bad_idx)} rows have NULLs in NOT NULL columns. Use skip_invalid_rows=true.")
                valid_rows = normalized_rows

            # COPY
            out = io.StringIO()
            writer = csv.DictWriter(out, fieldnames=required)
            writer.writeheader()
            for r in valid_rows:
                r2 = dict(r)
                if "hire_date" in r2 and r2["hire_date"] is not None:
                    r2["hire_date"] = r2["hire_date"].astimezone(timezone.utc).isoformat()
                writer.writerow(r2)
            out.seek(0)

            connection = db.connection()
            raw_conn = connection.connection
            with db.begin():
                with raw_conn.cursor() as cur:
                    cur.copy_expert(
                        f"COPY {table} ({','.join(required)}) FROM STDIN WITH CSV HEADER",
                        out
                    )
            return {"inserted": len(valid_rows), "skipped": errors}

        elif mode == "upsert":
            # === COPY to STAGING + MERGE (ON CONFLICT) ===
            cols = ",".join(required)
            with db.begin():
                db.execute(text(f"CREATE TEMP TABLE staging_{table} AS SELECT * FROM {table} WITH NO DATA;"))

                # COPY to staging
                out = io.StringIO()
                writer = csv.DictWriter(out, fieldnames=required)
                writer.writeheader()
                valid_rows = []
                for r in normalized_rows:
                    if all(r.get(c) is not None for c in required):
                        r2 = dict(r)
                        if "hire_date" in r2 and r2["hire_date"] is not None:
                            r2["hire_date"] = r2["hire_date"].astimezone(timezone.utc).isoformat()
                        writer.writerow(r2)
                        valid_rows.append(r)
                    elif not skip_invalid_rows:
                        raise ValueError("Row has NULLs in NOT NULL columns. Use skip_invalid_rows=true or clean the CSV.")
                    else:
                        errors += 1
                out.seek(0)

                connection = db.connection()
                raw_conn = connection.connection
                with raw_conn.cursor() as cur:
                    cur.copy_expert(
                        f"COPY staging_{table} ({cols}) FROM STDIN WITH CSV HEADER",
                        out
                    )

                # UPSERT (assuming PK = id)
                set_cols = [c for c in required if c != "id"]
                set_clause = ", ".join([f"{c}=excluded.{c}" for c in set_cols])
                db.execute(text(f"""
                    INSERT INTO {table} ({cols})
                    SELECT {cols} FROM staging_{table}
                    ON CONFLICT (id) DO UPDATE SET {set_clause}
                """))
                db.execute(text(f"DROP TABLE staging_{table};"))

            return {"inserted": len(valid_rows), "skipped": errors}

        else:
            raise ValueError("Invalid mode. Use 'insert' or 'upsert'.")

    else:
        # === SQLite ===
        cols = ",".join(required)
        placeholders = ",".join([f":{c}" for c in required])

        if mode == "insert":
            with db.begin():
                db.execute(text(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"), normalized_rows)
            return {"inserted": len(normalized_rows), "skipped": errors}

        elif mode == "upsert":
            # ON CONFLICT(id) DO UPDATE
            set_cols = [c for c in required if c != "id"]
            set_clause = ", ".join([f"{c}=excluded.{c}" for c in set_cols])
            with db.begin():
                db.execute(
                    text(f"""
                        INSERT INTO {table} ({cols}) VALUES ({placeholders})
                        ON CONFLICT(id) DO UPDATE SET {set_clause}
                    """),
                    normalized_rows
                )
            return {"inserted": len(normalized_rows), "skipped": errors}

        else:
            raise ValueError("Invalid mode. Use 'insert' or 'upsert'.")
