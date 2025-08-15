from typing import Literal

# Literal restricts the accepted values
TableName = Literal["departments", "jobs", "employees"]

# Standard expected headers for each table
EXPECTED_HEADERS = {
    "departments": ["id", "name"],
    "jobs": ["id", "title"],
    "employees": [
        "id",
        "name",
        "department_id",
        "job_id",
        "hire_date"
    ],
}

