from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Employee
from ..schemas import EmployeeBatch
from ..utils.batch import bulk_insert

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("/batch")
def batch_insert_employees(items: EmployeeBatch, db: Session = Depends(get_db)):
    """Inserta de 1 a 1000 registros en una sola transacción."""
    return bulk_insert(db, Employee, items)
