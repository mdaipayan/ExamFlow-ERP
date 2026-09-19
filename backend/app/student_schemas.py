from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    registration_number: str = Field(min_length=1, max_length=100)
    roll_number: str | None = Field(default=None, max_length=100)
    full_name: str = Field(min_length=2, max_length=200)
    gender: str | None = Field(default=None, max_length=40)
    mother_name: str | None = Field(default=None, max_length=200)
    status: str = Field(default="ACTIVE", max_length=30)


class EnrollmentCreate(BaseModel):
    programme_id: UUID
    admission_year: int = Field(ge=1900, le=date.today().year + 2)
    category: str | None = Field(default=None, max_length=50)
    entry_type: str = Field(default="REGULAR", max_length=40)


class StudentOut(StudentCreate):
    id: UUID


class EnrollmentOut(EnrollmentCreate):
    id: UUID
    student_id: UUID
