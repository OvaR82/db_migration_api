import csv
import io
from datetime import datetime
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def _valid_2021_hires():
    with open(DATA / "employees.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [
        r for r in rows
        if r["department_id"] and r["job_id"] and r["hire_date"] and r["name"]
        and datetime.fromisoformat(r["hire_date"].replace("Z", "+00:00")).year == 2021
    ]


def test_hiring_by_quarter(loaded):
    r = loaded.get("/metrics/hiring_by_quarter", params={"year": 2021})
    assert r.status_code == 200
    rows = r.json()
    assert rows
    assert set(rows[0]) == {"department", "job", "Q1", "Q2", "Q3", "Q4"}
    total = sum(row["Q1"] + row["Q2"] + row["Q3"] + row["Q4"] for row in rows)
    assert total == len(_valid_2021_hires())
    keys = [(row["department"], row["job"]) for row in rows]
    assert keys == sorted(keys)


def test_departments_above_mean(loaded):
    r = loaded.get("/metrics/departments_above_mean", params={"year": 2021})
    assert r.status_code == 200
    rows = r.json()
    assert rows

    counts = {}
    for e in _valid_2021_hires():
        counts[int(e["department_id"])] = counts.get(int(e["department_id"]), 0) + 1
    mean = sum(counts.values()) / len(counts)
    assert {row["id"] for row in rows} == {d for d, n in counts.items() if n > mean}
    hired = [row["hired"] for row in rows]
    assert hired == sorted(hired, reverse=True)


def test_metrics_csv_format(loaded):
    r = loaded.get("/metrics/departments_above_mean", params={"format": "csv"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    header = next(csv.reader(io.StringIO(r.text)))
    assert header == ["id", "department", "hired"]
