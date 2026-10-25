import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Read .env for local runs (uvicorn/alembic). Variables already set take precedence.
load_dotenv()

DB_URL = os.getenv("SQLITE_URL") or os.getenv(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/hr"
)

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

if engine.dialect.name == "sqlite":
    # SQLite only enforces foreign keys when enabled per connection.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fks(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
