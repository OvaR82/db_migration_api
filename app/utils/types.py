from typing import Literal

# Literal restringe los valores aceptados
TableName = Literal["departments", "jobs", "employees"]

# Encabezados estándar esperados para cada tabla
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
