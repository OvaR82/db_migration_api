# DB Migration API

A robust, production-ready REST API built with FastAPI for ingesting and managing HR-related data — departments, jobs, and employees — via structured CSV uploads. Ideal for use cases involving **data migration**, **ETL pipelines**, and **API-first ingestion workflows**.

## Features

- **CSV Data Ingestion**: Upload and process structured CSVs for employees, departments, and jobs
- **RESTful Endpoints**: Clear, consistent API for triggering ingestion
- **Database Migration**: Schema versioning and upgrades using Alembic
- **Monitoring & Metrics**: Built-in endpoints for hiring analytics
- **Dockerized**: Minimal and optimized production image
- **Automated Infra**: AWS cloud provisioning with Terraform (ECS, RDS, ALB, etc.)
- **Test Coverage**: Pytest unit tests and Locust performance testing

## Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Deployment](#deployment)
- [Configuration](#configuration)
- [Data Format](#data-format)
- [Development](#development)
- [Monitoring](#monitoring)
- [Contributing](#contributing)

## Architecture

```
db_migration_api/
├── app/ # FastAPI app
│ ├── routers/ # API route handlers
│ ├── models.py # SQLAlchemy models
│ ├── schemas.py # Pydantic input schemas
│ └── utils/ # CSV parsing and ingestion
├── config/ # Settings and header mappings
├── data/ # Example CSVs
├── infra/ # Terraform infrastructure
├── tests/ # Unit and load tests
├── Dockerfile # Production build
└── docker-compose.yml # Local container orchestration
```

## Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (optional)
- PostgreSQL or SQLite
- Terraform CLI (for AWS)

### Local Development

   ```bash
   git clone <repository-url>
   cd db_migration_api
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   $env:DATABASE_URL="sqlite:///./data/migration.sqlite3"
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

### Docker (Standalone or Compose)

1. **Using Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Access the application**
   - API: http://localhost:8000
   - Docs (Swagger): http://localhost:8000/docs

## API Documentation

### Base URL
```
http://localhost:8000
```

### Health Check

   GET /health – Basic readiness probe (used by ECS, ALB, etc.)

### Ingestion Endpoints

   Method	Endpoint	Description
   POST	/departments/upload	Upload departments CSV
   POST	/jobs/upload	Upload jobs CSV
   POST	/employees/upload	Upload employees CSV
   POST	/departments/batch	Upload departments via JSON payload
   POST	/jobs/batch	Upload jobs via JSON payload
   POST	/employees/batch	Upload employees via JSON payload
   POST	/ingest/csv	Dynamic ingestion using form + CSV

### Metrics Endpoints
   Method	Endpoint	Description
   GET	/metrics/hiring_by_quarter	Aggregated hires by department/job/quarter
   GET	/metrics/departments_above_mean	Departments with above-average hiring count

## Database Schema

### Tables

#### departments
   Column	Type	Description
   id	INTEGER	Primary key
   name	VARCHAR	Unique department name
#### jobs
   Column	Type	Description
   id	INTEGER	Primary key
   title	VARCHAR	Unique job title

#### employees
   Column	Type	Description
   id	INTEGER	Primary key
   name	VARCHAR	Employee name
   department_id	INTEGER	Foreign key to departments
   job_id	INTEGER	Foreign key to jobs
   hire_date	DATE	Date of hiring

## Testing

### Run Unit Tests

1. **Unit Tests**
   ```bash
   pytest tests/ -v
   ```

2. **Test CSV upload and DB writes**
   ```bash
   pytest tests/test_upload_*.py
   ```

3. **Run Load Tests with Locust**
   ```bash
   cd tests/performance
   locust -f locustfile.py --host=http://localhost:8000
   ```

### Test Structure
```
tests/
├── conftest.py              # Test configuration
├── test_ingest_*.py        # Ingestion tests
└── performance/
    └── locustfile.py       # Load testing
```

## Deployment

### Local Development
```bash
uvicorn app.main:app --reload
```

### Production (Dockerized with Gunicorn)
```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 2 --timeout 120
```

### AWS Deployment
1. **Initialize Terraform**
   ```bash
   cd infra/aws
   terraform init
   terraform plan
   terraform apply
   ```

2. **Provisioned resources:**
   ECR (Docker image)
   ECS (API service)
   RDS PostgreSQL
   ALB (HTTP access)
   CloudWatch Logs
   Secrets Manager (DATABASE_URL)

## Configuration

### Environment Variables
Create a `.env` file with:
```bash
# Database
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hr

# APP
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# AWS (Terraform)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

### Config Files
- `config/settings.yaml` – Ingestion behavior, upsert modes
- `config/header_mappings.yaml` – Accepted aliases for CSV headers

## Data Format

### CSV Requirements

#### departments.csv
```csv
id,name
1,Engineering
2,Marketing
3,Sales
```

#### jobs.csv
```csv
id,title
1,Software Engineer
2,Product Manager
3,Sales Representative
```

#### employees.csv
```csv
id,name,department_id,job_id,hire_date
1,John Doe,1,1,2023-01-15
2,Jane Smith,2,2,2023-02-20
```

## Development

### Code Style
- Follow PEP 8 guidelines
- Use black and ruff for linting and formatting

### Migrations (Alembic)
```bash
alembic revision --autogenerate -m "your message"
alembic upgrade head
alembic downgrade -1
```

### Adding a New Table
1. Define model in models.py
2. Add Pydantic schema in schemas.py
3. Update ingestion logic if applicable
4. Add test in tests/

## Monitoring

### Health & Observability
- **GET** /health → used by ALB / ECS
- /docs → Swagger UI
- Structured logging enabled by default

### Logs
- Local: stdout
- ECS: CloudWatch Logs group /ecs/<project>-api

## Contributing

1. Fork the repository
2. Create a branch: git checkout -b feature/your-feature
3. Commit your work: git commit -m 'Add your feature'
4. Push it: git push origin feature/your-feature
5. Open a Pull Request
