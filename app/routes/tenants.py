from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Property, Tenant, Unit, User
from app.routes.auth import get_current_user
from app.routes.properties import get_owned_property
from app.routes.units import get_owned_unit
from app.schemas.tenants import TenantCreate, TenantResponse, TenantUpdate


router = APIRouter(tags=["tenants"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_owned_tenant(db: Session, tenant_id: int, current_user: User) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    get_owned_unit(db, tenant.unit_id, current_user)
    return tenant


def get_owned_unit_in_property(
    db: Session,
    property_id: int,
    unit_id: int,
    current_user: User,
) -> Unit:
    get_owned_property(db, property_id, current_user)

    unit = db.get(Unit, unit_id)
    if unit is None or unit.property_id != property_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found in this property.",
        )

    return unit


def unit_has_active_tenant(
    db: Session,
    unit_id: int,
    tenant_id_to_ignore: int | None = None,
) -> bool:
    statement = select(Tenant).where(
        Tenant.unit_id == unit_id,
        Tenant.status == "active",
    )

    if tenant_id_to_ignore is not None:
        statement = statement.where(Tenant.id != tenant_id_to_ignore)

    active_tenant = db.scalar(statement)
    return active_tenant is not None


def landlord_has_active_tenant_with_phone(
    db: Session,
    owner_id: int,
    phone: str,
) -> bool:
    statement = (
        select(Tenant)
        .join(Unit, Tenant.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(
            Property.owner_id == owner_id,
            Tenant.phone == phone,
            Tenant.status == "active",
        )
    )

    active_tenant = db.scalar(statement)
    return active_tenant is not None


@router.post(
    "/properties/{property_id}/units/{unit_id}/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tenant for a property unit",
    name="create_tenant_for_property_unit",
    operation_id="create_tenant_for_property_unit",
)
def create_tenant(
    property_id: int,
    unit_id: int,
    tenant_data: TenantCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Tenant:
    unit = get_owned_unit_in_property(db, property_id, unit_id, current_user)

    if tenant_data.status == "active":
        if landlord_has_active_tenant_with_phone(
            db,
            current_user.id,
            tenant_data.phone,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This tenant is already assigned to another active unit.",
            )

        if unit_has_active_tenant(db, unit.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This unit already has an active tenant.",
            )

    tenant = Tenant(
        unit_id=unit.id,
        full_name=tenant_data.full_name,
        phone=tenant_data.phone,
        national_id=tenant_data.national_id,
        emergency_contact=tenant_data.emergency_contact,
        move_in_date=tenant_data.move_in_date,
        rent_due_day=tenant_data.rent_due_day,
        notes=tenant_data.notes,
        status=tenant_data.status,
    )

    if tenant.status == "active":
        unit.status = "occupied"

    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get(
    "/properties/{property_id}/units/{unit_id}/tenants",
    response_model=list[TenantResponse],
    summary="List tenants for a property unit",
    name="list_tenants_for_property_unit",
    operation_id="list_tenants_for_property_unit",
)
def read_unit_tenants(
    property_id: int,
    unit_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> list[Tenant]:
    unit = get_owned_unit_in_property(db, property_id, unit_id, current_user)

    return list(
        db.scalars(
            select(Tenant)
            .where(Tenant.unit_id == unit.id)
            .order_by(Tenant.created_at.desc())
        )
    )


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Get a tenant",
    name="get_tenant",
    operation_id="get_tenant",
)
def read_tenant(
    tenant_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Tenant:
    return get_owned_tenant(db, tenant_id, current_user)


@router.put(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Update a tenant",
    name="update_tenant",
    operation_id="update_tenant",
)
def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Tenant:
    tenant = get_owned_tenant(db, tenant_id, current_user)
    unit = db.get(Unit, tenant.unit_id)

    updates = tenant_data.model_dump(exclude_unset=True)

    if updates.get("status") == "active" and unit_has_active_tenant(
        db,
        tenant.unit_id,
        tenant.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This unit already has an active tenant.",
        )

    for field, value in updates.items():
        setattr(tenant, field, value)

    if tenant.status == "moved_out" and unit is not None:
        unit.status = "vacant"
    elif tenant.status == "active" and unit is not None:
        unit.status = "occupied"

    db.commit()
    db.refresh(tenant)
    return tenant


@router.delete(
    "/tenants/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tenant",
    name="delete_tenant",
    operation_id="delete_tenant",
)
def delete_tenant(
    tenant_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    tenant = get_owned_tenant(db, tenant_id, current_user)
    unit = db.get(Unit, tenant.unit_id)

    if tenant.status == "active" and unit is not None:
        unit.status = "vacant"

    db.delete(tenant)
    db.commit()
