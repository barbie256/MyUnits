from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.constants import DEFAULT_CURRENCY, SUPPORTED_CURRENCIES


UserRole = Literal["landlord", "manager", "caretaker"]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = "landlord"
    currency: str = DEFAULT_CURRENCY

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: EmailStr) -> str:
        return str(email).strip().lower()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, currency: str) -> str:
        normalized_currency = currency.strip().upper()
        if normalized_currency not in SUPPORTED_CURRENCIES:
            allowed = ", ".join(SUPPORTED_CURRENCIES)
            raise ValueError(f"Currency must be one of: {allowed}")

        return normalized_currency


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
    currency: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
