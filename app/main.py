from fastapi import FastAPI
from .routers import ingest, departments, jobs, employees, metrics

# Initialize FastAPI application
app = FastAPI(title="DB Migration API", version="1.1.0")

# Register routers
app.include_router(ingest.router)
app.include_router(departments.router)
app.include_router(jobs.router)
app.include_router(employees.router)
app.include_router(metrics.router)

# Health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}
