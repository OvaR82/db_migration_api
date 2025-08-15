from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..schemas import EmployeeBatch
from ..models import Employee
import csv
from io import StringIO

router = APIRouter(prefix="/employees", tags=["employees"])

# Ingestion from CSV file
@router.post("/upload")
async def upload_employees(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.DictReader(StringIO(decoded))
    payload = []

    for row in reader:
        # Convert dates
        if "hire_date" in row and row["hire_date"]:
            row["hire_date"] = datetime.fromisoformat(row["hire_date"].replace("Z", "")).date()
        
        # Convert empty strings to None
        for key in ["job_id", "department_id"]:
            if row.get(key) == "":
                row[key] = None

        payload.append(row)

    try:
        with db.begin():
            db.bulk_insert_mappings(Employee, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Insert failed: {e}")

    return {"inserted": len(payload)}

# Ingestion from JSON
@router.post("/batch")
def batch_insert_employees(items: EmployeeBatch, db: Session = Depends(get_db)):
    if not (1 <= len(items) <= 1000):
        raise HTTPException(status_code=400, detail="Batch size must be 1..1000")

    payload = [i.model_dump() for i in items]

    try:
        with db.begin():
            db.bulk_insert_mappings(Employee, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Insert failed: {e}")

    return {"inserted": len(payload)}
