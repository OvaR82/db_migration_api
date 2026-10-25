import logging
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..db import get_db
from ..utils.csv_ingest import ingest_csv, read_source_file
from ..utils.types import TableName

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])

Mode = Literal["insert", "ignore", "update"]
MODE_DESCRIPTION = "Defaults to ingest.upsert in settings.yaml"
SKIP_DESCRIPTION = "Skip invalid rows instead of failing the whole load"


async def run_ingest(
    db: Session,
    table: TableName,
    file: UploadFile | None,
    source_path: str | None,
    skip_invalid_rows: bool,
    mode: str | None,
) -> dict:
    """Read the CSV (uploaded or from DATA_DIR), load it and map errors to HTTP responses."""
    if not file and not source_path:
        raise HTTPException(status_code=400, detail="Provide either 'file' or 'source_path'.")

    try:
        content = (await file.read()).decode("utf-8-sig") if file else read_source_file(source_path)
        result = ingest_csv(db, table, content, skip_invalid_rows=skip_invalid_rows, mode=mode)
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="The file must be UTF-8 encoded.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        logger.exception("ingest %s: integrity error", table)
        raise HTTPException(
            status_code=409,
            detail="Integrity conflict: duplicate id or reference to a missing department/job.",
        )
    except SQLAlchemyError:
        logger.exception("ingest %s: database error", table)
        raise HTTPException(status_code=500, detail="Database error.")

    return {"status": "ok", "table": table, **result}


@router.post("/csv")
async def ingest_csv_upload(
    table: TableName = Form(...),
    file: UploadFile | None = File(None),
    source_path: str | None = Form(None, description="Name of a CSV file inside the server data directory"),
    skip_invalid_rows: bool = Form(False, description=SKIP_DESCRIPTION),
    mode: Mode | None = Form(None, description=MODE_DESCRIPTION),
    db: Session = Depends(get_db),
):
    return await run_ingest(db, table, file, source_path, skip_invalid_rows, mode)
