import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_jobs_csv():
    file_path = os.path.join("data", "jobs.csv")
    assert os.path.exists(file_path), "jobs.csv file not found"

    with open(file_path, "rb") as f:
        files = {"file": ("jobs.csv", f, "text/csv")}
        response = client.post("/jobs/upload", files=files)

    print(response.json())  # useful for debugging
    assert response.status_code == 200
    assert "inserted" in response.json()
    assert response.json()["inserted"] > 0
