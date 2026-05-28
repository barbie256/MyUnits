from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import MaintenanceRequest, Property, Tenant, Unit, User
from app.routes.auth import get_current_user
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceResponse,
    MaintenanceUpdate,
)


router = APIRouter(tags=["maintenance"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_owned_unit_for_maintenance(
    db: Session,
    unit_id: int,
    current_user: User,
) -> Unit:
    unit = db.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found.",
        )

    property_item = db.get(Property, unit.property_id)
    if property_item is None or property_item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access. This unit is not connected to your property.",
        )

    return unit


def get_active_tenant_for_unit(db: Session, unit_id: int) -> Tenant | None:
    return db.scalar(
        select(Tenant).where(
            Tenant.unit_id == unit_id,
            Tenant.status == "active",
        )
    )


def get_owned_maintenance_request(
    db: Session,
    request_id: int,
    current_user: User,
) -> MaintenanceRequest:
    maintenance_request = db.get(MaintenanceRequest, request_id)
    if maintenance_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance request not found.",
        )

    property_item = db.get(Property, maintenance_request.property_id)
    if property_item is None or property_item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Unauthorized access. This maintenance request is not connected "
                "to your property."
            ),
        )

    return maintenance_request


@router.post(
    "/units/{unit_id}/maintenance",
    response_model=MaintenanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a maintenance request for a unit",
)
def create_maintenance_request(
    unit_id: int,
    request_data: MaintenanceCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> MaintenanceRequest:
    unit = get_owned_unit_for_maintenance(db, unit_id, current_user)
    active_tenant = get_active_tenant_for_unit(db, unit.id)

    maintenance_request = MaintenanceRequest(
        property_id=unit.property_id,
        unit_id=unit.id,
        tenant_id=active_tenant.id if active_tenant is not None else None,
        issue_title=request_data.issue_title,
        description=request_data.description,
        priority=request_data.priority,
        status=request_data.status,
    )

    db.add(maintenance_request)
    db.commit()
    db.refresh(maintenance_request)
    return maintenance_request


@router.get(
    "/units/{unit_id}/maintenance",
    response_model=list[MaintenanceResponse],
    summary="List maintenance requests for a unit",
)
def read_unit_maintenance_requests(
    unit_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> list[MaintenanceRequest]:
    unit = get_owned_unit_for_maintenance(db, unit_id, current_user)

    return list(
        db.scalars(
            select(MaintenanceRequest)
            .where(MaintenanceRequest.unit_id == unit.id)
            .order_by(MaintenanceRequest.created_at.desc())
        )
    )


@router.get(
    "/maintenance/{request_id}",
    response_model=MaintenanceResponse,
    summary="Get a maintenance request",
)
def read_maintenance_request(
    request_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> MaintenanceRequest:
    return get_owned_maintenance_request(db, request_id, current_user)


@router.put(
    "/maintenance/{request_id}",
    response_model=MaintenanceResponse,
    summary="Update a maintenance request",
)
def update_maintenance_request(
    request_id: int,
    request_data: MaintenanceUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> MaintenanceRequest:
    maintenance_request = get_owned_maintenance_request(db, request_id, current_user)

    updates = request_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(maintenance_request, field, value)

    db.commit()
    db.refresh(maintenance_request)
    return maintenance_request


@router.delete(
    "/maintenance/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a maintenance request",
)
def delete_maintenance_request(
    request_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    maintenance_request = get_owned_maintenance_request(db, request_id, current_user)

    db.delete(maintenance_request)
    db.commit()
