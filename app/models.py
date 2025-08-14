from sqlalchemy import String, Integer, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    hire_date: Mapped["Date"] = mapped_column(Date, nullable=True)

    department = relationship("Department")
    job = relationship("Job")
