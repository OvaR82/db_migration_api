from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..utils.csv_ingest import ingest_csv, _open_source
from ..utils.types import TableName

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/csv")
async def ingest_csv_upload(
    table: TableName = Form(...),
    file: UploadFile = File(None),
    source_path: str | None = Form(None),
    skip_invalid_rows: bool = Form(False, description="Omitir filas inválidas en vez de fallar toda la carga"),
    db: Session = Depends(get_db)
):
    if not file and not source_path:
        raise HTTPException(status_code=400, detail="Proveer 'file' o 'source_path'.")

    content = (await file.read()).decode("utf-8") if file else _open_source(source_path).read()

    try:
        result = ingest_csv(db, table, content, skip_invalid_rows=skip_invalid_rows)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "ok", "table": table, **(result or {})}

