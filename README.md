# DB Migration API

REST API (FastAPI + SQLAlchemy + Alembic) that loads historical HR data from CSV files into a SQL database, accepts batch inserts of 1–1000 rows, and exposes two hiring metrics.

## Requirements

- Python 3.11 (the Docker image uses 3.11)
- PostgreSQL 16 (or SQLite for quick local tests)
- Docker & Docker Compose (optional)
- Terraform >= 1.5 (optional, AWS deployment)

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # set DATABASE_URL (or SQLITE_URL)
alembic upgrade head
uvicorn app.main:app --reload
```

`.env` is read automatically by the app and by Alembic. Variables already set in the environment take precedence.

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLAlchemy URL for PostgreSQL | `postgresql+psycopg://postgres:postgres@localhost:5432/hr` |
| `SQLITE_URL` | If set, overrides `DATABASE_URL` (e.g. `sqlite:///./local.db`) | — |
| `INGEST_DATA_DIR` | Only directory `source_path` may read from | `./data` |

## Docker

```bash
docker compose up --build
```

The API container waits for Postgres, runs `alembic upgrade head` and starts Gunicorn on http://localhost:8000 (docs at `/docs`).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/ingest/csv` | Load a CSV into `departments`, `jobs` or `employees` |
| POST | `/departments/batch` | Insert 1–1000 departments (JSON) |
| POST | `/jobs/batch` | Insert 1–1000 jobs (JSON) |
| POST | `/employees/batch` | Insert 1–1000 employees (JSON) |
| GET | `/metrics/hiring_by_quarter` | Hires per department and job, split by quarter |
| GET | `/metrics/departments_above_mean` | Departments that hired more than the mean |

### `POST /ingest/csv` (multipart form)

| Field | Description |
|-------|-------------|
| `table` | `departments`, `jobs` or `employees` (required) |
| `file` | CSV upload, **or** |
| `source_path` | File name inside `INGEST_DATA_DIR` (e.g. `employees.csv`) |
| `skip_invalid_rows` | `true` to skip invalid rows instead of rejecting the whole file |
| `mode` | `insert` (fail on existing id), `ignore` (skip existing ids) or `update` (overwrite). Defaults to `ingest.upsert` in `config/settings.yaml` |

Load order matters (employees reference departments and jobs):

```bash
curl -F table=departments -F source_path=departments.csv http://localhost:8000/ingest/csv
curl -F table=jobs        -F source_path=jobs.csv        http://localhost:8000/ingest/csv
curl -F table=employees   -F source_path=employees.csv -F skip_invalid_rows=true http://localhost:8000/ingest/csv
```

The response includes `inserted`, `skipped` and up to 100 `errors` (`{"row": <line>, "error": <reason>}`); every skipped row is also logged. The load is all-or-nothing: if the database rejects a row (duplicate id, unknown department/job) nothing is written and the API returns 409.

### Batch insert

```bash
curl -X POST http://localhost:8000/employees/batch -H "Content-Type: application/json" \
  -d '[{"id": 5000, "name": "Ana Pérez", "department_id": 1, "job_id": 1, "hire_date": "2021-03-01"}]'
```

### Metrics

Both accept `year` (default `2021`), `format` (`json` | `csv`) and `include_unknown` (default `true`).

```bash
curl "http://localhost:8000/metrics/hiring_by_quarter?year=2021"
curl "http://localhost:8000/metrics/departments_above_mean?year=2021&format=csv"
```

## Data model

| Table | Columns |
|-------|---------|
| `departments` | `id` INTEGER PK, `name` VARCHAR(120) UNIQUE |
| `jobs` | `id` INTEGER PK, `title` VARCHAR(120) UNIQUE |
| `employees` | `id` INTEGER PK, `name` VARCHAR(80), `department_id` FK → departments, `job_id` FK → jobs, `hire_date` DATE |

## CSV format

Files need a header row. Column aliases are configured in `config/header_mappings.yaml` (e.g. `dept_name` → `name`).

```csv
id,name
1,Product Management
```

```csv
id,title
1,Marketing Assistant
```

```csv
id,name,hire_date,department_id,job_id
1,Harold Vogt,2021-11-07T02:48:42Z,2,96
```

`hire_date` is ISO 8601; it is converted to UTC and stored as a date. Future dates are rejected. When ingesting a CSV, every employee field is required.

## Configuration

`config/settings.yaml`:

- `ingest.upsert`: default `mode` for `/ingest/csv` (`insert` | `ignore` | `update`).
- `ingest.use_copy_for_postgres`: load through `COPY` into a temp table (faster for large files).

## Tests

```bash
pytest
pytest --cov=app
```

Tests run against a temporary SQLite database and use the sample files in `data/`.

## AWS deployment (Terraform)

`infra/aws` creates ECR, RDS PostgreSQL, a Secrets Manager secret with `DATABASE_URL`, and an ECS Fargate service behind a public ALB (HTTP).

```bash
cd infra/aws
cp terraform.tfvars.example terraform.tfvars   # set db_password
terraform init
terraform plan
terraform apply
```

Then build the image and push it to the ECR repo from the `ecr_repo` output with the tag in `image_tag`. `terraform.tfvars` and the state files contain the database password and are git-ignored; keep them out of the repository.

> The API has no authentication. Do not expose it publicly with real data without adding auth and HTTPS.
