from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Unit, User
from app.routes.auth import get_current_user
from app.routes.properties import get_owned_property
from app.schemas.units import UnitCreate, UnitResponse, UnitUpdate


router = APIRouter(tags=["units"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_owned_unit(db: Session, unit_id: int, current_user: User) -> Unit:
    unit = db.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found.",
        )

    get_owned_property(db, unit.property_id, current_user)
    return unit


@router.post(
    "/properties/{property_id}/units",
    response_model=UnitResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_unit(
    property_id: int,
    unit_data: UnitCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Unit:
    property_item = get_owned_property(db, property_id, current_user)

    unit = Unit(
        property_id=property_item.id,
        unit_name=unit_data.unit_name,
        rent_amount=unit_data.rent_amount,
        status=unit_data.status,
    )

    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.get("/properties/{property_id}/units", response_model=list[UnitResponse])
def read_property_units(
    property_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> list[Unit]:
    property_item = get_owned_property(db, property_id, current_user)

    return list(
        db.scalars(
            select(Unit)
            .where(Unit.property_id == property_item.id)
            .order_by(Unit.created_at.desc())
        )
    )


@router.get("/units/{unit_id}", response_model=UnitResponse)
def read_unit(
    unit_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Unit:
    return get_owned_unit(db, unit_id, current_user)


@router.put("/units/{unit_id}", response_model=UnitResponse)
def update_unit(
    unit_id: int,
    unit_data: UnitUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Unit:
    unit = get_owned_unit(db, unit_id, current_user)

    updates = unit_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(unit, field, value)

    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(
    unit_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    unit = get_owned_unit(db, unit_id, current_user)

    db.delete(unit)
    db.commit()
