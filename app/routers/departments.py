from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Department
from ..schemas import DepartmentBatch
from ..utils.batch import bulk_insert

router = APIRouter(prefix="/departments", tags=["departments"])


@router.post("/batch")
def batch_insert_departments(items: DepartmentBatch, db: Session = Depends(get_db)):
    """Inserta de 1 a 1000 registros en una sola transacción."""
    return bulk_insert(db, Department, items)
