from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants import SUPPORTED_PROPERTY_TYPES


PropertyType = Literal[
    "apartment",
    "hostel",
    "shops",
    "residential",
    "commercial",
    "office",
    "warehouse",
    "mixed_use",
    "student_housing",
]


class PropertyCreate(BaseModel):
    property_name: str = Field(min_length=1, max_length=150)
    location: str = Field(min_length=1, max_length=255)
    property_type: PropertyType
    description: str | None = None

    @field_validator("property_type", mode="before")
    @classmethod
    def validate_property_type(cls, property_type: object) -> object:
        if not isinstance(property_type, str):
            raise ValueError("Property type must be text.")

        normalized_property_type = property_type.strip().lower()
        if normalized_property_type not in SUPPORTED_PROPERTY_TYPES:
            allowed = ", ".join(SUPPORTED_PROPERTY_TYPES)
            raise ValueError(f"Property type must be one of: {allowed}")

        return normalized_property_type


class PropertyUpdate(BaseModel):
    property_name: str | None = Field(default=None, min_length=1, max_length=150)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    property_type: PropertyType | None = None
    description: str | None = None

    @field_validator("property_type", mode="before")
    @classmethod
    def validate_property_type(cls, property_type: object) -> object:
        if property_type is None:
            return None

        if not isinstance(property_type, str):
            raise ValueError("Property type must be text.")

        normalized_property_type = property_type.strip().lower()
        if normalized_property_type not in SUPPORTED_PROPERTY_TYPES:
            allowed = ", ".join(SUPPORTED_PROPERTY_TYPES)
            raise ValueError(f"Property type must be one of: {allowed}")

        return normalized_property_type


class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    property_name: str
    location: str
    property_type: str
    description: str | None
    created_at: datetime
