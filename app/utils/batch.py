import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def bulk_insert(db: Session, model, items) -> dict:
    """Insert a batch in a single transaction (all or nothing)."""
    payload = [i.model_dump() for i in items]
    try:
        with db.begin():
            db.execute(model.__table__.insert(), payload)
    except IntegrityError:
        logger.exception("batch %s: integrity error", model.__tablename__)
        raise HTTPException(
            status_code=409,
            detail="Integrity conflict: duplicate id or missing reference.",
        )
    except SQLAlchemyError:
        logger.exception("batch %s: database error", model.__tablename__)
        raise HTTPException(status_code=500, detail="Database error.")
    return {"inserted": len(payload)}
