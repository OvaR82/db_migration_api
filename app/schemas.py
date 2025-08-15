from pydantic import BaseModel, Field, conlist
from datetime import date
from typing import List

# Input schema for Department
class DepartmentIn(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=120)

# Input schema for Job
class JobIn(BaseModel):
    id: int
    title: str = Field(min_length=1, max_length=120)

# Input schema for Employee
class EmployeeIn(BaseModel):
    id: int
    name: str
    department_id: int
    job_id: int
    hire_date: date

# Batches (1 to 1000 elements)
DepartmentBatch = conlist(DepartmentIn, min_length=1, max_length=1000)
JobBatch        = conlist(JobIn,        min_length=1, max_length=1000)
EmployeeBatch   = conlist(EmployeeIn,   min_length=1, max_length=1000)

