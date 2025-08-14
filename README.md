# Database Migration API
A robust FastAPI-based REST API for managing database migrations and data ingestion with support for CSV file processing, metrics tracking, and comprehensive CRUD operations.

## Features

- **FastAPI Framework**: High-performance, modern Python web framework
- **Database Migrations**: Alembic-based database schema management
- **CSV Data Ingestion**: Automated processing and validation of CSV files
- **RESTful API**: Complete CRUD operations for departments, employees, jobs, and metrics
- **Docker Support**: Containerized deployment with Docker and Docker Compose
- **AWS Infrastructure**: Terraform configurations for cloud deployment
- **Comprehensive Testing**: Pytest-based test suite
- **Type Safety**: Pydantic models for data validation

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Data Ingestion](#data-ingestion)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Docker & Docker Compose (optional)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd db_migration_api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the application**
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker Installation

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Access the application**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Usage

### API Documentation

Once the application is running, you can access:
- **Interactive API docs**: http://localhost:8000/docs
- **Alternative API docs**: http://localhost:8000/redoc

### Quick Start

1. **Ingest sample data**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/ingest/all" \
     -H "accept: application/json"
   ```

2. **Get metrics**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/metrics/employees-by-quarter" \
     -H "accept: application/json"
   ```

## 🔗 API Endpoints

### Departments
- `GET /api/v1/departments` - List all departments
- `POST /api/v1/departments` - Create a new department
- `GET /api/v1/departments/{id}` - Get department by ID
- `PUT /api/v1/departments/{id}` - Update department
- `DELETE /api/v1/departments/{id}` - Delete department

### Employees
- `GET /api/v1/employees` - List all employees with pagination
- `POST /api/v1/employees` - Create a new employee
- `GET /api/v1/employees/{id}` - Get employee by ID
- `PUT /api/v1/employees/{id}` - Update employee
- `DELETE /api/v1/employees/{id}` - Delete employee

### Jobs
- `GET /api/v1/jobs` - List all jobs
- `POST /api/v1/jobs` - Create a new job
- `GET /api/v1/jobs/{id}` - Get job by ID
- `PUT /api/v1/jobs/{id}` - Update job
- `DELETE /api/v1/jobs/{id}` - Delete job

### Data Ingestion
- `POST /api/v1/ingest/departments` - Ingest departments from CSV
- `POST /api/v1/ingest/jobs` - Ingest jobs from CSV
- `POST /api/v1/ingest/employees` - Ingest employees from CSV
- `POST /api/v1/ingest/all` - Ingest all data from CSV files

### Metrics
- `GET /api/v1/metrics/employees-by-quarter` - Get employees hired by quarter
- `GET /api/v1/metrics/departments-above-mean` - Get departments above mean hiring

## Database Schema

### Tables

#### departments
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| department | VARCHAR(255) | Department name |

#### jobs
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| job | VARCHAR(255) | Job title |

#### employees
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(255) | Employee name |
| datetime | TIMESTAMP | Hire date |
| department_id | INTEGER | Foreign key to departments |
| job_id | INTEGER | Foreign key to jobs |

## Data Ingestion

### CSV File Structure

The system expects CSV files with the following structure:

#### departments.csv
```csv
id,department
1,Engineering
2,Marketing
3,Sales
```

#### jobs.csv
```csv
id,job
1,Software Engineer
2,Data Analyst
3,Product Manager
```

#### employees.csv
```csv
id,name,datetime,department_id,job_id
1,John Doe,2021-07-15 09:00:00,1,1
2,Jane Smith,2021-08-20 10:30:00,2,2
```

### Configuration

Configuration files are located in `config/`:
- `header_mappings.yaml`: CSV column mappings
- `settings.yaml`: Application settings

## Testing

### Run tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_employees.py
```

### Test structure
```
tests/
├── conftest.py          # Test configuration
├── test_departments.py  # Department tests
├── test_employees.py    # Employee tests
├── test_jobs.py         # Job tests
├── test_ingest.py       # Data ingestion tests
└── test_metrics.py      # Metrics tests
```

## Deployment

### Local Development
```bash
uvicorn app.main:app --reload
```

### Docker
```bash
docker-compose up --build
```

### AWS Deployment

1. **Configure AWS credentials**
   ```bash
   aws configure
   ```

2. **Deploy with Terraform**
   ```bash
   cd infra/aws
   terraform init
   terraform plan
   terraform apply
   ```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost/db` |
| `API_HOST` | API host binding | `0.0.0.0` |
| `API_PORT` | API port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting
