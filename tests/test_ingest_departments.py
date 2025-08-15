import os
import sqlite3
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_routes():
    # Print all registered routes (useful for debugging)
    for route in app.routes:
        print(f"{route.path} -> {route.name}")

def test_upload_departments_csv():
    # Send a CSV file to the departments upload endpoint
    file_path = os.path.join("data", "departments.csv")
    with open(file_path, "rb") as f:
        files = {"file": ("departments.csv", f, "text/csv")}
        response = client.post("/departments/upload", files=files)

    print(response.json())  # for debugging
    assert response.status_code == 200
    assert "inserted" in response.json()
    assert response.json()["inserted"] > 0

def test_rows_inserted():
    # Check directly in SQLite that rows were inserted into the departments table
    conn = sqlite3.connect("test.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM departments")
    row_count = cursor.fetchone()[0]
    conn.close()
    assert row_count > 0
