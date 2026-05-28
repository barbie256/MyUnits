from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


MaintenancePriority = Literal["low", "medium", "high"]
MaintenanceStatus = Literal["pending", "in_progress", "fixed"]


class MaintenanceCreate(BaseModel):
    issue_title: str = Field(min_length=1, max_length=150)
    description: str | None = None
    priority: MaintenancePriority = "medium"
    status: MaintenanceStatus = "pending"


class MaintenanceUpdate(BaseModel):
    issue_title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    priority: MaintenancePriority | None = None
    status: MaintenanceStatus | None = None


class MaintenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    unit_id: int
    tenant_id: int | None
    issue_title: str
    description: str | None
    priority: MaintenancePriority
    status: MaintenanceStatus
    created_at: datetime
