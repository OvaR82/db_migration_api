from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..schemas import EmployeeBatch
from ..models import Employee

router = APIRouter(prefix="/employees", tags=["employees"])

@router.post("/batch")
def batch_insert_employees(items: EmployeeBatch, db: Session = Depends(get_db)):
    if not (1 <= len(items) <= 1000):
        raise HTTPException(status_code=400, detail="Batch size must be 1..1000")
    try:
        with db.begin():
            db.bulk_insert_mappings(Employee, [i.model_dump() for i in items])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Insert failed: {e}")
    return {"inserted": len(items)}
