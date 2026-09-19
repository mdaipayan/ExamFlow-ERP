from uuid import UUID

from pydantic import BaseModel, Field


class RegisterStudentsRequest(BaseModel):
    student_ids: list[UUID] = Field(min_length=1, max_length=5000)


class SetEligibilityRequest(BaseModel):
    attendance_percent: float | None = Field(default=None, ge=0, le=100)
    eligible_for_ese: bool
    reason: str | None = Field(default=None, max_length=500)
    grade_override: str | None = Field(default=None, max_length=10)
