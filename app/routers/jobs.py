from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Job
from ..schemas import JobBatch
from ..utils.batch import bulk_insert
from .ingest import MODE_DESCRIPTION, SKIP_DESCRIPTION, Mode, run_ingest

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/upload")
async def upload_jobs(
    file: UploadFile = File(...),
    skip_invalid_rows: bool = Form(False, description=SKIP_DESCRIPTION),
    mode: Mode | None = Form(None, description=MODE_DESCRIPTION),
    db: Session = Depends(get_db),
):
    """Load a jobs CSV (same as POST /ingest/csv with table=jobs)."""
    return await run_ingest(db, "jobs", file, None, skip_invalid_rows, mode)


@router.post("/batch")
def batch_insert_jobs(items: JobBatch, db: Session = Depends(get_db)):
    """Insert 1 to 1000 records in a single transaction."""
    return bulk_insert(db, Job, items)
