"""Prueba de carga con Locust.

    pip install locust
    locust -f tests/performance/locustfile.py --host http://localhost:8000

Usa mode=update para que las cargas repetidas no fallen por id duplicado.
"""
import os

from locust import HttpUser, between, task

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


class DataMigrationUser(HttpUser):
    wait_time = between(1, 3)

    def _upload(self, table: str, **extra):
        with open(os.path.join(DATA_DIR, f"{table}.csv"), "rb") as f:
            self.client.post(
                f"/{table}/upload",
                files={"file": (f"{table}.csv", f, "text/csv")},
                data={"mode": "update", **extra},
                name=f"/{table}/upload",
            )

    @task
    def upload_departments(self):
        self._upload("departments")

    @task
    def upload_jobs(self):
        self._upload("jobs")

    @task
    def upload_employees(self):
        self._upload("employees", skip_invalid_rows="true")

    @task(3)
    def metrics(self):
        self.client.get("/metrics/hiring_by_quarter")
        self.client.get("/metrics/departments_above_mean")
