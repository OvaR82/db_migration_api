import os
import csv
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_employees_csv():
    file_path = os.path.join("data", "employees.csv")
    assert os.path.exists(file_path), "employees.csv file not found"

    errors = []

    # Validate CSV content before upload
    with open(file_path, newline='', encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader, start=1):
            required_fields = ["id", "name", "hire_date"]
            for field in required_fields:
                if row[field].strip() == "":
                    errors.append(f"Row {i}: field '{field}' is empty")
            for field in ["department_id", "job_id"]:
                if row[field].strip() == "":
                    print(f"Warning: Row {i}, field '{field}' is empty (will be treated as None)")

    # If there were errors, show them all together
    assert not errors, "CSV validation errors:\n" + "\n".join(errors)

    # Upload only if CSV is valid
    with open(file_path, "rb") as f:
        files = {"file": ("employees.csv", f, "text/csv")}
        response = client.post("/employees/upload", files=files)

    print(response.json())
    assert response.status_code == 200, f"Upload failed: {response.json()}"
