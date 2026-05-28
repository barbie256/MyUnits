from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TenantStatus = Literal["active", "moved_out"]


class TenantCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=1, max_length=30)
    national_id: str | None = Field(default=None, max_length=50)
    emergency_contact: str | None = Field(default=None, max_length=100)
    move_in_date: date
    rent_due_day: int = Field(ge=1, le=31)
    notes: str | None = None
    status: TenantStatus = "active"


class TenantUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, min_length=1, max_length=30)
    national_id: str | None = Field(default=None, max_length=50)
    emergency_contact: str | None = Field(default=None, max_length=100)
    move_in_date: date | None = None
    rent_due_day: int | None = Field(default=None, ge=1, le=31)
    notes: str | None = None
    status: TenantStatus | None = None


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    full_name: str
    phone: str
    national_id: str | None
    emergency_contact: str | None
    move_in_date: date
    rent_due_day: int
    notes: str | None
    status: str
    created_at: datetime
