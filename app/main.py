from fastapi import FastAPI
from .routers import ingest, departments, jobs, employees, metrics

app = FastAPI(title="DB Migration API", version="1.1.0")

app.include_router(ingest.router)
app.include_router(departments.router)
app.include_router(jobs.router)
app.include_router(employees.router)
app.include_router(metrics.router)

@app.get("/health")
def health():
    return {"status": "ok"}
