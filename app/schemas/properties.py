from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PropertyType = Literal["apartment", "hostel", "shops", "residential"]


class PropertyCreate(BaseModel):
    property_name: str = Field(min_length=1, max_length=150)
    location: str = Field(min_length=1, max_length=255)
    property_type: PropertyType
    description: str | None = None


class PropertyUpdate(BaseModel):
    property_name: str | None = Field(default=None, min_length=1, max_length=150)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    property_type: PropertyType | None = None
    description: str | None = None


class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    property_name: str
    location: str
    property_type: str
    description: str | None
    created_at: datetime
