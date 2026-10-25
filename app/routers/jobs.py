from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Job
from ..schemas import JobBatch
from ..utils.batch import bulk_insert

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/batch")
def batch_insert_jobs(items: JobBatch, db: Session = Depends(get_db)):
    """Inserta de 1 a 1000 registros en una sola transacción."""
    return bulk_insert(db, Job, items)
