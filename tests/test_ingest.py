import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def _csv_rows(name):
    with open(DATA / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_ingest_sample_data(loaded):
    r = loaded.post(
        "/ingest/csv",
        data={"table": "employees", "source_path": "employees.csv", "skip_invalid_rows": "true"},
    )
    body = r.json()
    total = len(_csv_rows("employees.csv"))
    assert body["inserted"] + body["skipped"] == total
    assert body["skipped"] > 0
    assert all({"row", "error"} <= e.keys() for e in body["errors"])


def test_ingest_without_skip_fails_on_first_invalid_row(client):
    client.post("/ingest/csv", data={"table": "departments", "source_path": "departments.csv"})
    client.post("/ingest/csv", data={"table": "jobs", "source_path": "jobs.csv"})
    r = client.post("/ingest/csv", data={"table": "employees", "source_path": "employees.csv"})
    assert r.status_code == 400
    assert "Error en fila" in r.json()["detail"]


def test_ingest_upload_and_modes(client):
    files = {"file": ("d.csv", "id,dept_name\n1,Sales\n2,Legal\n", "text/csv")}
    r = client.post("/ingest/csv", data={"table": "departments", "mode": "insert"}, files=files)
    assert r.status_code == 200
    assert r.json()["inserted"] == 2

    # Mismo id con insert -> conflicto
    files = {"file": ("d.csv", "id,name\n1,Ventas\n", "text/csv")}
    r = client.post("/ingest/csv", data={"table": "departments", "mode": "insert"}, files=files)
    assert r.status_code == 409

    # update -> sobreescribe
    r = client.post("/ingest/csv", data={"table": "departments", "mode": "update"}, files=files)
    assert r.status_code == 200
    r = client.post("/ingest/csv", data={"table": "departments", "mode": "ignore"}, files=files)
    assert r.status_code == 200


def test_ingest_missing_headers(client):
    files = {"file": ("d.csv", "foo,bar\n1,x\n", "text/csv")}
    r = client.post("/ingest/csv", data={"table": "departments"}, files=files)
    assert r.status_code == 400
    assert "missing" in r.json()["detail"]


def test_ingest_rejects_paths_outside_data_dir(client):
    for path in ("../.env", "../app/main.py", "http://169.254.169.254/latest/meta-data"):
        r = client.post("/ingest/csv", data={"table": "departments", "source_path": path})
        assert r.status_code == 400, path


def test_ingest_requires_file_or_path(client):
    assert client.post("/ingest/csv", data={"table": "jobs"}).status_code == 400


def test_upload_endpoints_per_table(client):
    for table in ("departments", "jobs", "employees"):
        with open(DATA / f"{table}.csv", "rb") as f:
            r = client.post(
                f"/{table}/upload",
                files={"file": (f"{table}.csv", f, "text/csv")},
                data={"skip_invalid_rows": "true"},
            )
        assert r.status_code == 200, r.text
        assert r.json()["table"] == table
        assert r.json()["inserted"] > 0
