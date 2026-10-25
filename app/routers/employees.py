from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Employee
from ..schemas import EmployeeBatch
from ..utils.batch import bulk_insert
from .ingest import MODE_DESCRIPTION, SKIP_DESCRIPTION, Mode, run_ingest

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("/upload")
async def upload_employees(
    file: UploadFile = File(...),
    skip_invalid_rows: bool = Form(False, description=SKIP_DESCRIPTION),
    mode: Mode | None = Form(None, description=MODE_DESCRIPTION),
    db: Session = Depends(get_db),
):
    """Load a employees CSV (same as POST /ingest/csv with table=employees)."""
    return await run_ingest(db, "employees", file, None, skip_invalid_rows, mode)


@router.post("/batch")
def batch_insert_employees(items: EmployeeBatch, db: Session = Depends(get_db)):
    """Insert 1 to 1000 records in a single transaction."""
    return bulk_insert(db, Employee, items)
