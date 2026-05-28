from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


UnitStatus = Literal["vacant", "occupied", "reserved"]


class UnitCreate(BaseModel):
    unit_name: str = Field(min_length=1, max_length=80)
    rent_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    status: UnitStatus = "vacant"


class UnitUpdate(BaseModel):
    unit_name: str | None = Field(default=None, min_length=1, max_length=80)
    rent_amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    status: UnitStatus | None = None


class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    unit_name: str
    rent_amount: Decimal
    status: str
    created_at: datetime
