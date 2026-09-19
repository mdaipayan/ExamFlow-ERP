from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class ExaminationCreate(BaseModel):
    programme_id: UUID
    semester_id: UUID
    regulation_version_id: UUID
    name: str = Field(min_length=2, max_length=200)
    term_label: str = Field(min_length=2, max_length=100)
    starts_on: date | None = None
    ends_on: date | None = None


class ExaminationOut(BaseModel):
    id: UUID
    programme_id: UUID
    semester_id: UUID
    regulation_version_id: UUID
    name: str
    term_label: str
    status: str
    starts_on: date | None
    ends_on: date | None


class AddCourseRequest(BaseModel):
    course_id: UUID
