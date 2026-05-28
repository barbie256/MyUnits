from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Payment, Property, Receipt, Tenant, Unit, User
from app.routes.auth import get_current_user
from app.schemas.receipts import ReceiptResponse


router = APIRouter(tags=["receipts"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def ensure_receipt_belongs_to_user(
    db: Session,
    receipt: Receipt,
    current_user: User,
) -> Receipt:
    payment = db.get(Payment, receipt.payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    unit = db.get(Unit, payment.unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    property_item = db.get(Property, unit.property_id)
    if property_item is None or property_item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access. This receipt is not connected to your property.",
        )

    return receipt


def get_owned_receipt(
    db: Session,
    receipt_id: int,
    current_user: User,
) -> Receipt:
    receipt = db.get(Receipt, receipt_id)
    if receipt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found.",
        )

    return ensure_receipt_belongs_to_user(db, receipt, current_user)


def get_owned_payment_for_receipts(
    db: Session,
    payment_id: int,
    current_user: User,
) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    unit = db.get(Unit, payment.unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    property_item = db.get(Property, unit.property_id)
    if property_item is None or property_item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access. This payment is not connected to your property.",
        )

    return payment


def get_owned_tenant_for_receipts(
    db: Session,
    tenant_id: int,
    current_user: User,
) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    unit = db.get(Unit, tenant.unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    property_item = db.get(Property, unit.property_id)
    if property_item is None or property_item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access. This tenant is not connected to your property.",
        )

    return tenant


@router.get(
    "/receipts/{receipt_id}",
    response_model=ReceiptResponse,
    summary="Get a receipt",
)
def read_receipt(
    receipt_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Receipt:
    return get_owned_receipt(db, receipt_id, current_user)


@router.get(
    "/payments/{payment_id}/receipt",
    response_model=ReceiptResponse,
    summary="Get the receipt for a payment",
)
def read_payment_receipt(
    payment_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Receipt:
    payment = get_owned_payment_for_receipts(db, payment_id, current_user)
    receipt = db.scalar(select(Receipt).where(Receipt.payment_id == payment.id))
    if receipt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found.",
        )

    return receipt


@router.get(
    "/tenants/{tenant_id}/receipts",
    response_model=list[ReceiptResponse],
    summary="List receipts for a tenant",
)
def read_tenant_receipts(
    tenant_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> list[Receipt]:
    tenant = get_owned_tenant_for_receipts(db, tenant_id, current_user)

    return list(
        db.scalars(
            select(Receipt)
            .where(Receipt.tenant_id == tenant.id)
            .order_by(Receipt.payment_date.desc(), Receipt.created_at.desc())
        )
    )
