from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants import SUPPORTED_ID_DOCUMENT_TYPES


TenantStatus = Literal["active", "moved_out"]
IdDocumentType = Literal["national_id", "passport", "refugee_id", "other"]


class TenantCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=1, max_length=30)
    nationality: str | None = Field(default=None, max_length=80)
    id_document_type: IdDocumentType | None = Field(default=None, max_length=30)
    id_document_number: str | None = Field(default=None, max_length=80)
    id_document_image_url: str | None = Field(default=None, max_length=500)
    emergency_contact: str | None = Field(default=None, max_length=100)
    move_in_date: date
    rent_due_day: int = Field(ge=1, le=31)
    notes: str | None = None
    status: TenantStatus = "active"

    @field_validator("id_document_type", mode="before")
    @classmethod
    def validate_id_document_type(cls, id_document_type: object) -> object:
        if id_document_type is None:
            return None

        if not isinstance(id_document_type, str):
            raise ValueError("ID document type must be text.")

        normalized_type = id_document_type.strip().lower()
        if normalized_type not in SUPPORTED_ID_DOCUMENT_TYPES:
            allowed = ", ".join(SUPPORTED_ID_DOCUMENT_TYPES)
            raise ValueError(f"ID document type must be one of: {allowed}")

        return normalized_type


class TenantUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, min_length=1, max_length=30)
    nationality: str | None = Field(default=None, max_length=80)
    id_document_type: IdDocumentType | None = Field(default=None, max_length=30)
    id_document_number: str | None = Field(default=None, max_length=80)
    id_document_image_url: str | None = Field(default=None, max_length=500)
    emergency_contact: str | None = Field(default=None, max_length=100)
    move_in_date: date | None = None
    rent_due_day: int | None = Field(default=None, ge=1, le=31)
    notes: str | None = None
    status: TenantStatus | None = None

    @field_validator("id_document_type", mode="before")
    @classmethod
    def validate_id_document_type(cls, id_document_type: object) -> object:
        if id_document_type is None:
            return None

        if not isinstance(id_document_type, str):
            raise ValueError("ID document type must be text.")

        normalized_type = id_document_type.strip().lower()
        if normalized_type not in SUPPORTED_ID_DOCUMENT_TYPES:
            allowed = ", ".join(SUPPORTED_ID_DOCUMENT_TYPES)
            raise ValueError(f"ID document type must be one of: {allowed}")

        return normalized_type


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    full_name: str
    phone: str
    nationality: str | None
    id_document_type: str | None
    id_document_number: str | None
    id_document_image_url: str | None
    emergency_contact: str | None
    move_in_date: date
    rent_due_day: int
    notes: str | None
    status: str
    created_at: datetime
