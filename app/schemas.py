from datetime import date

from pydantic import BaseModel, Field, conlist


class DepartmentIn(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=120)


class JobIn(BaseModel):
    id: int
    title: str = Field(min_length=1, max_length=120)


class EmployeeIn(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=80)
    department_id: int
    job_id: int
    hire_date: date


# Para batch (1..1000)
DepartmentBatch = conlist(DepartmentIn, min_length=1, max_length=1000)
JobBatch = conlist(JobIn, min_length=1, max_length=1000)
EmployeeBatch = conlist(EmployeeIn, min_length=1, max_length=1000)
