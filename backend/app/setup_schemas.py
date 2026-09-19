from pydantic import BaseModel, EmailStr, Field


class InitialSetupRequest(BaseModel):
    institution_name: str = Field(min_length=2, max_length=200)
    institution_code: str = Field(min_length=2, max_length=50)
    admin_name: str = Field(min_length=2, max_length=150)
    admin_email: EmailStr
    admin_password: str = Field(min_length=12, max_length=200)
