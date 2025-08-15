import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Default to PostgreSQL, override with SQLITE_URL if provided
DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/hr")
if os.getenv("SQLITE_URL"):
    DB_URL = os.getenv("SQLITE_URL")

# Detect testing mode
TESTING = os.getenv("TESTING", "0") == "1"

# Define database URL based on environment
if TESTING:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
else:
    SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://user:password@localhost/dbname"

# Create SQLAlchemy engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if TESTING else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
class Base(DeclarativeBase):
    pass

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
