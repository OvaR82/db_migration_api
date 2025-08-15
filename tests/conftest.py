import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db
from app.main import app

# Force the use of SQLite for testing
TEST_DB_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fixture for setting up the test database
@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # (Optional) Drop all tables after tests complete
    Base.metadata.drop_all(bind=engine)

# Fixture to override the get_db dependency in FastAPI
@pytest.fixture(autouse=True)
def override_get_db():
    def _get_test_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = _get_test_db
