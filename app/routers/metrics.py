from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from starlette.responses import Response
from ..db import get_db
import csv, io

router = APIRouter(prefix="/metrics", tags=["metrics"])

def _csv_response(rows, headers: list[str], filename: str) -> Response:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=headers)
    w.writeheader()
    for r in rows:
        d = dict(r) if not isinstance(r, dict) else r
        w.writerow({h: d.get(h, "") for h in headers})
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/hiring_by_quarter")
def hiring_by_quarter(
    year: int = Query(2021, ge=1900, le=2100),
    format: str = Query("json", pattern="^(json|csv)$"),
    include_unknown: bool = Query(True, description="Include rows without department/job as '(Unknown)'"),
    db: Session = Depends(get_db),
):
    dialect = db.bind.dialect.name
    params = {"y": year, "y_next": year + 1}

    if dialect.startswith("postgresql"):
        unknown_filter = "" if include_unknown else "AND e.department_id IS NOT NULL AND e.job_id IS NOT NULL"
        sql = text(f"""
            WITH base AS (
              SELECT
                COALESCE(d.name, '(Unknown)') AS department,
                COALESCE(j.title, '(Unknown)') AS job,
                EXTRACT(QUARTER FROM e.hire_date)::int AS q
              FROM employees e
              LEFT JOIN departments d ON d.id = e.department_id
              LEFT JOIN jobs j        ON j.id = e.job_id
              WHERE e.hire_date >= make_date(:y,1,1)
                AND e.hire_date <  make_date(:y_next,1,1)
                {unknown_filter}
            )
            SELECT department, job,
              SUM(CASE WHEN q=1 THEN 1 ELSE 0 END) AS "Q1",
              SUM(CASE WHEN q=2 THEN 1 ELSE 0 END) AS "Q2",
              SUM(CASE WHEN q=3 THEN 1 ELSE 0 END) AS "Q3",
              SUM(CASE WHEN q=4 THEN 1 ELSE 0 END) AS "Q4"
            FROM base
            GROUP BY department, job
            ORDER BY department ASC, job ASC;
        """)
    else:
        unknown_filter = "" if include_unknown else "AND e.department_id IS NOT NULL AND e.job_id IS NOT NULL"
        sql = text(f"""
          -- Normalize timestamp to 'YYYY-MM-DD HH:MM:SS' (without timezone)
          WITH norm AS (
            SELECT
              COALESCE(d.name, '(Unknown)') AS department,
              COALESCE(j.title, '(Unknown)') AS job,
              -- Replace 'T' with space and truncate to 19 chars to remove 'Z' and offsets
              substr(replace(e.hire_date, 'T', ' '), 1, 19) AS dt
            FROM employees e
            LEFT JOIN departments d ON d.id = e.department_id
            LEFT JOIN jobs j        ON j.id = e.job_id
            WHERE e.hire_date IS NOT NULL
              {unknown_filter}
          ),
          base AS (
            SELECT
              department,
              job,
              CAST(strftime('%m', dt) AS INTEGER) AS m
            FROM norm
            WHERE dt >= (:y || '-01-01 00:00:00')
              AND dt <  (:y_next || '-01-01 00:00:00')
          )
          SELECT
            department,
            job,
            SUM(CASE WHEN m BETWEEN 1 AND 3  THEN 1 ELSE 0 END) AS "Q1",
            SUM(CASE WHEN m BETWEEN 4 AND 6  THEN 1 ELSE 0 END) AS "Q2",
            SUM(CASE WHEN m BETWEEN 7 AND 9  THEN 1 ELSE 0 END) AS "Q3",
            SUM(CASE WHEN m BETWEEN 10 AND 12 THEN 1 ELSE 0 END) AS "Q4"
          FROM base
          GROUP BY department, job
          ORDER BY department ASC, job ASC;
      """)

    rows = db.execute(sql, params).mappings().all()
    if format == "csv":
        return _csv_response(rows, ["department", "job", "Q1", "Q2", "Q3", "Q4"], f"hiring_by_quarter_{year}.csv")
    return rows

@router.get("/departments_above_mean")
def departments_above_mean(
    year: int = Query(2021, ge=1900, le=2100),
    format: str = Query("json", pattern="^(json|csv)$"),
    include_unknown: bool = Query(True, description="Include '(Unknown)' as department when missing"),
    db: Session = Depends(get_db),
):
    dialect = db.bind.dialect.name
    if dialect.startswith("postgresql"):
        date_cond = "e.hire_date >= make_date(:y,1,1) AND e.hire_date < make_date(:y_next,1,1)"
    else:
        date_cond = "datetime(e.hire_date) >= datetime(:y || '-01-01T00:00:00Z') AND datetime(e.hire_date) < datetime(:y_next || '-01-01T00:00:00Z')"

    # If unknowns are not allowed, require department to be not null
    base_where = date_cond + ("" if include_unknown else " AND e.department_id IS NOT NULL")

    sql = text(f"""
        WITH hires AS (
          SELECT
            COALESCE(d.id, -1)                      AS id,
            COALESCE(d.name, '(Unknown)')           AS department,
            COUNT(*)                                AS hired
          FROM employees e
          LEFT JOIN departments d ON d.id = e.department_id
          WHERE {base_where}
          GROUP BY COALESCE(d.id, -1), COALESCE(d.name, '(Unknown)')
        )
        SELECT id, department, hired
        FROM hires
        WHERE hired > (SELECT AVG(hired) FROM hires)
        ORDER BY hired DESC, department ASC;
    """)
    params = {"y": year, "y_next": year + 1}
    rows = db.execute(sql, params).mappings().all()
    if format == "csv":
        return _csv_response(rows, ["id", "department", "hired"], f"departments_above_mean_{year}.csv")
    return rows
