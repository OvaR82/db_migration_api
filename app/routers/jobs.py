from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..schemas import JobBatch
from ..models import Job
import csv
from io import StringIO

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Ingestion from CSV file
@router.post("/upload")
async def upload_jobs(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.DictReader(StringIO(decoded))
    payload = [row for row in reader]

    try:
        with db.begin():
            db.bulk_insert_mappings(Job, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Insert failed: {e}")

    return {"inserted": len(payload)}

# Ingestion from JSON
@router.post("/batch")
def batch_insert_jobs(items: JobBatch, db: Session = Depends(get_db)):
    if not (1 <= len(items) <= 1000):
        raise HTTPException(status_code=400, detail="Batch size must be 1..1000")

    payload = [i.model_dump() for i in items]

    try:
        with db.begin():
            db.bulk_insert_mappings(Job, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Insert failed: {e}")

    return {"inserted": len(payload)}
