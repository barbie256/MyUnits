from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Tenant, Unit, User
from app.routes.auth import get_current_user
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


@router.post(
    "/units/{unit_id}/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tenant(
    unit_id: int,
    tenant_data: TenantCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Tenant:
    unit = get_owned_unit(db, unit_id, current_user)

    if tenant_data.status == "active" and unit_has_active_tenant(db, unit.id):
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


@router.get("/units/{unit_id}/tenants", response_model=list[TenantResponse])
def read_unit_tenants(
    unit_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> list[Tenant]:
    unit = get_owned_unit(db, unit_id, current_user)

    return list(
        db.scalars(
            select(Tenant)
            .where(Tenant.unit_id == unit.id)
            .order_by(Tenant.created_at.desc())
        )
    )


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
def read_tenant(
    tenant_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Tenant:
    return get_owned_tenant(db, tenant_id, current_user)


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
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


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
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
