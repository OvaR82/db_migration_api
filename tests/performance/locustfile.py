from locust import HttpUser, task, between
import os

class DataMigrationUser(HttpUser):
    # Wait time between tasks (simulates user think time)
    wait_time = between(1, 3)

    @task
    def upload_employees(self):
        # Uploads employees.csv to the ingestion endpoint
        file_path = os.path.join("data", "employees.csv")
        with open(file_path, "rb") as f:
            files = {'file': ('employees.csv', f, 'text/csv')}
            self.client.post("/ingest/employees", files=files)

    @task
    def upload_departments(self):
        # Uploads departments.csv to the ingestion endpoint
        file_path = os.path.join("data", "departments.csv")
        with open(file_path, "rb") as f:
            files = {'file': ('departments.csv', f, 'text/csv')}
            self.client.post("/ingest/departments", files=files)

    @task
    def upload_jobs(self):
        # Uploads jobs.csv to the ingestion endpoint
        file_path = os.path.join("data", "jobs.csv")
        with open(file_path, "rb") as f:
            files = {'file': ('jobs.csv', f, 'text/csv')}
            self.client.post("/ingest/jobs", files=files)
