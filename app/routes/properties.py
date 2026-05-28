from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Property, User
from app.routes.auth import get_current_user
from app.schemas.properties import PropertyCreate, PropertyResponse, PropertyUpdate


router = APIRouter(prefix="/properties", tags=["properties"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_property_or_404(db: Session, property_id: int) -> Property:
    property_item = db.get(Property, property_id)
    if property_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found.",
        )

    return property_item


def get_owned_property(db: Session, property_id: int, current_user: User) -> Property:
    property_item = get_property_or_404(db, property_id)
    if property_item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this property.",
        )

    return property_item


def check_duplicate_property(
    db: Session,
    owner_id: int,
    property_name: str,
    location: str,
    property_id_to_ignore: int | None = None,
) -> None:
    query = select(Property).where(
        Property.owner_id == owner_id,
        Property.property_name == property_name,
        Property.location == location,
    )

    if property_id_to_ignore is not None:
        query = query.where(Property.id != property_id_to_ignore)

    existing_property = db.scalar(query)
    if existing_property is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a property with this name and location.",
        )


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_property(
    property_data: PropertyCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Property:
    check_duplicate_property(
        db=db,
        owner_id=current_user.id,
        property_name=property_data.property_name,
        location=property_data.location,
    )

    property_item = Property(
        owner_id=current_user.id,
        property_name=property_data.property_name,
        location=property_data.location,
        property_type=property_data.property_type,
        description=property_data.description,
    )

    db.add(property_item)
    db.commit()
    db.refresh(property_item)
    return property_item


@router.get("", response_model=list[PropertyResponse])
def read_properties(db: DbSession, current_user: CurrentUser) -> list[Property]:
    return list(
        db.scalars(
            select(Property)
            .where(Property.owner_id == current_user.id)
            .order_by(Property.created_at.desc())
        )
    )


@router.get("/{property_id}", response_model=PropertyResponse)
def read_property(
    property_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Property:
    return get_owned_property(db, property_id, current_user)


@router.put("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: int,
    property_data: PropertyUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Property:
    property_item = get_owned_property(db, property_id, current_user)

    updates = property_data.model_dump(exclude_unset=True)
    updated_property_name = updates.get("property_name", property_item.property_name)
    updated_location = updates.get("location", property_item.location)
    check_duplicate_property(
        db=db,
        owner_id=current_user.id,
        property_name=updated_property_name,
        location=updated_location,
        property_id_to_ignore=property_item.id,
    )

    for field, value in updates.items():
        setattr(property_item, field, value)

    db.commit()
    db.refresh(property_item)
    return property_item


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    property_item = get_owned_property(db, property_id, current_user)

    db.delete(property_item)
    db.commit()
