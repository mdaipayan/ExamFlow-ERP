from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class MarkEntryRequest(BaseModel):
    student_id: UUID
    course_id: UUID
    component_code: str = Field(min_length=1, max_length=50)
    marks: Decimal | None = Field(default=None, ge=0)


class MarksImportResult(BaseModel):
    batch_id: UUID
    created: int
    updated: int
    errors: list[dict]


class ValidationSummary(BaseModel):
    examination_id: UUID
    errors: int
    warnings: int
    issues: list[dict]
