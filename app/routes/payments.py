from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Payment, Property, Tenant, Unit, User
from app.routes.auth import get_current_user
from app.schemas.payments import PaymentCreate, PaymentResponse, PaymentUpdate


router = APIRouter(tags=["payments"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def calculate_balance_after_payment(rent_amount: Decimal, amount_paid: Decimal) -> Decimal:
    balance = rent_amount - amount_paid
    if balance < 0:
        return Decimal("0")

    return balance


def get_owned_tenant_for_payments(
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


def get_owned_payment(
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


@router.post(
    "/tenants/{tenant_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a tenant payment",
)
def create_payment(
    tenant_id: int,
    payment_data: PaymentCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Payment:
    tenant = get_owned_tenant_for_payments(db, tenant_id, current_user)
    unit = db.get(Unit, tenant.unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    payment = Payment(
        tenant_id=tenant.id,
        unit_id=unit.id,
        amount_paid=payment_data.amount_paid,
        payment_method=payment_data.payment_method,
        payment_date=payment_data.payment_date,
        month_paid_for=payment_data.month_paid_for,
        balance_after_payment=calculate_balance_after_payment(
            unit.rent_amount,
            payment_data.amount_paid,
        ),
        recorded_by=current_user.id,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.get(
    "/tenants/{tenant_id}/payments",
    response_model=list[PaymentResponse],
    summary="List payments for a tenant",
)
def read_tenant_payments(
    tenant_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> list[Payment]:
    tenant = get_owned_tenant_for_payments(db, tenant_id, current_user)

    return list(
        db.scalars(
            select(Payment)
            .where(Payment.tenant_id == tenant.id)
            .order_by(Payment.payment_date.desc(), Payment.created_at.desc())
        )
    )


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
    summary="Get a payment",
)
def read_payment(
    payment_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Payment:
    return get_owned_payment(db, payment_id, current_user)


@router.put(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
    summary="Update a payment",
)
def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Payment:
    payment = get_owned_payment(db, payment_id, current_user)
    updates = payment_data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(payment, field, value)

    if "amount_paid" in updates:
        unit = db.get(Unit, payment.unit_id)
        if unit is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found.",
            )

        payment.balance_after_payment = calculate_balance_after_payment(
            unit.rent_amount,
            payment.amount_paid,
        )

    db.commit()
    db.refresh(payment)
    return payment


@router.delete(
    "/payments/{payment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a payment",
)
def delete_payment(
    payment_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    payment = get_owned_payment(db, payment_id, current_user)

    db.delete(payment)
    db.commit()
