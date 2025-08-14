from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..schemas import DepartmentBatch
from ..models import Department

router = APIRouter(prefix="/departments", tags=["departments"])

@router.post("/batch")
def batch_insert_departments(items: DepartmentBatch, db: Session = Depends(get_db)):
    if not (1 <= len(items) <= 1000):
        raise HTTPException(status_code=400, detail="Batch size must be 1..1000")

    payload = [i.model_dump() for i in items]

    try:
        with db.begin():
            db.bulk_insert_mappings(Department, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Insert failed: {e}")

    return {"inserted": len(payload)}
