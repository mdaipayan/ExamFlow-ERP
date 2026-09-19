from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSummary(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    institution_id: str | None
    roles: list[str]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary
