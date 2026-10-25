import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def bulk_insert(db: Session, model, items) -> dict:
    """Inserta un lote en una sola transacción (todo o nada)."""
    payload = [i.model_dump() for i in items]
    try:
        with db.begin():
            db.execute(model.__table__.insert(), payload)
    except IntegrityError:
        logger.exception("batch %s: error de integridad", model.__tablename__)
        raise HTTPException(
            status_code=409,
            detail="Conflicto de integridad: id duplicado o referencia inexistente.",
        )
    except SQLAlchemyError:
        logger.exception("batch %s: error de base de datos", model.__tablename__)
        raise HTTPException(status_code=500, detail="Error de base de datos.")
    return {"inserted": len(payload)}
