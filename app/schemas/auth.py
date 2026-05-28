from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


UserRole = Literal["landlord", "manager", "caretaker"]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = "landlord"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: EmailStr) -> str:
        return str(email).strip().lower()


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: EmailStr) -> str:
        return str(email).strip().lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str
    role: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
