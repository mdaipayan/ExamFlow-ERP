from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ProgrammeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    level: str = Field(min_length=1, max_length=50)
    duration_semesters: int | None = Field(default=None, ge=1, le=20)


class ProgrammeOut(ProgrammeCreate):
    id: UUID


class SemesterCreate(BaseModel):
    number: int = Field(ge=1, le=20)
    name: str = Field(min_length=1, max_length=100)


class SemesterOut(SemesterCreate):
    id: UUID
    programme_id: UUID


class CourseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    credits: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    course_type: str = Field(default="THEORY", min_length=1, max_length=40)
    is_audit: bool = False


class CourseOut(CourseCreate):
    id: UUID


class ComponentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    max_marks: Decimal = Field(gt=0, le=1000)
    weightage: Decimal = Field(ge=0, le=100)
    minimum_marks: Decimal | None = Field(default=None, ge=0)
    sort_order: int = Field(default=1, ge=1, le=100)


class ComponentOut(ComponentCreate):
    id: UUID
    course_id: UUID


class RegulationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)


class RegulationOut(RegulationCreate):
    id: UUID


class RegulationVersionCreate(BaseModel):
    version_label: str = Field(min_length=1, max_length=100)
    effective_from: date | None = None
    effective_to: date | None = None
    parameters: dict = Field(default_factory=dict)
