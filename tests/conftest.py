import os
import tempfile

import pytest

# Set the URL before importing the app (app.db creates the engine on import).
_tmpdir = tempfile.mkdtemp()
os.environ["SQLITE_URL"] = f"sqlite:///{os.path.join(_tmpdir, 'test.db')}"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def loaded(client):
    """Load the sample CSV files from data/."""
    for table in ("departments", "jobs", "employees"):
        r = client.post(
            "/ingest/csv",
            data={"table": table, "source_path": f"{table}.csv", "skip_invalid_rows": "true"},
        )
        assert r.status_code == 200, r.text
    return client
