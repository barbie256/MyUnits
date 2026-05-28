from collections import defaultdict
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Payment, Property, Tenant, Unit, User
from app.routes.auth import get_current_user
from app.schemas.payments import PaymentCreate, PaymentResponse, PaymentUpdate


router = APIRouter(tags=["payments"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

MONTH_NAMES = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def get_month_sort_key(month_paid_for: str) -> tuple[int, int]:
    month_text = month_paid_for.strip().lower()
    normalized_text = month_text.replace("/", "-")
    parts = normalized_text.replace(",", " ").replace("-", " ").split()

    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        first_number = int(parts[0])
        second_number = int(parts[1])
        if first_number > 31 and 1 <= second_number <= 12:
            return first_number, second_number
        if second_number > 31 and 1 <= first_number <= 12:
            return second_number, first_number

    if len(parts) == 2:
        if parts[0] in MONTH_NAMES and parts[1].isdigit():
            return int(parts[1]), MONTH_NAMES[parts[0]]
        if parts[1] in MONTH_NAMES and parts[0].isdigit():
            return int(parts[0]), MONTH_NAMES[parts[1]]

    if len(parts) == 1 and parts[0] in MONTH_NAMES:
        return 0, MONTH_NAMES[parts[0]]

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "month_paid_for must be a recognizable month like "
            "'2026-06', 'June 2026', or 'June'."
        ),
    )


def calculate_balance_after_payment(
    rent_amount: Decimal,
    total_available_for_month: Decimal,
) -> Decimal:
    balance = rent_amount - total_available_for_month
    if balance < 0:
        return Decimal("0")

    return balance


def calculate_credit_amount(
    rent_amount: Decimal,
    total_available_for_month: Decimal,
) -> Decimal:
    credit_amount = total_available_for_month - rent_amount
    if credit_amount < 0:
        return Decimal("0")

    return credit_amount


def determine_payment_status(balance_after_payment: Decimal) -> str:
    if balance_after_payment > 0:
        return "partial"

    return "paid"


def get_total_paid_for_month(
    db: Session,
    tenant_id: int,
    month_paid_for: str,
    exclude_payment_id: int | None = None,
) -> Decimal:
    query = select(func.coalesce(func.sum(Payment.amount_paid), 0)).where(
        Payment.tenant_id == tenant_id,
        Payment.month_paid_for == month_paid_for,
    )

    if exclude_payment_id is not None:
        query = query.where(Payment.id != exclude_payment_id)

    return Decimal(db.scalar(query) or 0)


def get_previous_credit_available(
    db: Session,
    tenant_id: int,
    unit_id: int,
    month_paid_for: str,
    exclude_payment_id: int | None = None,
) -> Decimal:
    current_month_key = get_month_sort_key(month_paid_for)
    payments = list(
        db.scalars(
            select(Payment).where(
                Payment.tenant_id == tenant_id,
                Payment.unit_id == unit_id,
                Payment.month_paid_for != month_paid_for,
            )
        )
    )

    unit = db.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    rent_amount = Decimal(unit.rent_amount)
    month_totals: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    month_saved_credit: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))

    for payment in payments:
        if exclude_payment_id is not None and payment.id == exclude_payment_id:
            continue

        month_key = get_month_sort_key(payment.month_paid_for)
        if month_key >= current_month_key:
            continue

        month_totals[month_key] += Decimal(payment.amount_paid)
        if payment.credit_amount > 0:
            month_saved_credit[month_key] = max(
                month_saved_credit[month_key],
                Decimal(payment.credit_amount),
            )

    credit_balance = Decimal("0")
    for month_key in sorted(month_totals):
        saved_credit = month_saved_credit[month_key]
        if saved_credit > 0:
            credit_balance = saved_credit
        else:
            total_available_for_month = credit_balance + month_totals[month_key]
            credit_balance = calculate_credit_amount(
                rent_amount,
                total_available_for_month,
            )

    return credit_balance


def calculate_month_payment_totals(
    db: Session,
    tenant_id: int,
    unit_id: int,
    rent_amount: Decimal,
    month_paid_for: str,
    exclude_payment_id: int | None = None,
    extra_amount_paid: Decimal = Decimal("0"),
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, str]:
    total_paid_for_month = get_total_paid_for_month(
        db,
        tenant_id,
        month_paid_for,
        exclude_payment_id=exclude_payment_id,
    )
    total_paid_for_month += extra_amount_paid
    available_previous_credit = get_previous_credit_available(
        db,
        tenant_id,
        unit_id,
        month_paid_for,
        exclude_payment_id=exclude_payment_id,
    )
    previous_credit_applied = min(available_previous_credit, rent_amount)
    total_available_for_month = total_paid_for_month + available_previous_credit
    balance_after_payment = calculate_balance_after_payment(
        rent_amount,
        total_available_for_month,
    )
    credit_amount = calculate_credit_amount(
        rent_amount,
        total_available_for_month,
    )

    return (
        total_paid_for_month,
        previous_credit_applied,
        total_available_for_month,
        balance_after_payment,
        credit_amount,
        determine_payment_status(balance_after_payment),
    )


def add_calculated_totals_to_payment(
    payment: Payment,
    total_paid_for_month: Decimal,
    previous_credit_applied: Decimal,
    total_available_for_month: Decimal,
    balance_after_payment: Decimal,
    credit_amount: Decimal,
    payment_status: str,
) -> Payment:
    payment.total_paid_for_month = total_paid_for_month
    payment.previous_credit_applied = previous_credit_applied
    payment.total_available_for_month = total_available_for_month
    payment.balance_after_payment = balance_after_payment
    payment.credit_amount = credit_amount
    payment.payment_status = payment_status
    return payment


def add_payment_totals_to_response(db: Session, payment: Payment) -> Payment:
    unit = db.get(Unit, payment.unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return add_calculated_totals_to_payment(
        payment,
        *calculate_month_payment_totals(
            db,
            payment.tenant_id,
            payment.unit_id,
            unit.rent_amount,
            payment.month_paid_for,
        ),
    )


def validate_zero_payment(
    amount_paid: Decimal,
    previous_credit_applied: Decimal,
) -> None:
    if amount_paid == 0 and previous_credit_applied == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount can be 0 only when previous credit is being applied.",
        )


def save_month_totals_on_payment(
    payment: Payment,
    total_paid_for_month: Decimal,
    previous_credit_applied: Decimal,
    total_available_for_month: Decimal,
    balance_after_payment: Decimal,
    credit_amount: Decimal,
    payment_status: str,
) -> Payment:
    payment.balance_after_payment = balance_after_payment
    payment.credit_amount = credit_amount
    payment.payment_status = payment_status
    return add_calculated_totals_to_payment(
        payment,
        total_paid_for_month,
        previous_credit_applied,
        total_available_for_month,
        balance_after_payment,
        credit_amount,
        payment_status,
    )


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

    (
        total_paid_for_month,
        previous_credit_applied,
        total_available_for_month,
        balance_after_payment,
        credit_amount,
        payment_status,
    ) = calculate_month_payment_totals(
        db,
        tenant.id,
        unit.id,
        unit.rent_amount,
        payment_data.month_paid_for,
        extra_amount_paid=payment_data.amount_paid,
    )
    validate_zero_payment(payment_data.amount_paid, previous_credit_applied)

    payment = Payment(
        tenant_id=tenant.id,
        unit_id=unit.id,
        amount_paid=payment_data.amount_paid,
        payment_method=payment_data.payment_method,
        payment_date=payment_data.payment_date,
        month_paid_for=payment_data.month_paid_for,
        balance_after_payment=balance_after_payment,
        credit_amount=credit_amount,
        payment_status=payment_status,
        recorded_by=current_user.id,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)
    return add_calculated_totals_to_payment(
        payment,
        total_paid_for_month,
        previous_credit_applied,
        total_available_for_month,
        balance_after_payment,
        credit_amount,
        payment_status,
    )


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

    payments = list(
        db.scalars(
            select(Payment)
            .where(Payment.tenant_id == tenant.id)
            .order_by(Payment.payment_date.desc(), Payment.created_at.desc())
        )
    )

    for payment in payments:
        add_payment_totals_to_response(db, payment)

    return payments


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
    payment = get_owned_payment(db, payment_id, current_user)
    return add_payment_totals_to_response(db, payment)


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

    if {"amount_paid", "month_paid_for"} & updates.keys():
        unit = db.get(Unit, payment.unit_id)
        if unit is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found.",
            )

        (
            total_paid_for_month,
            previous_credit_applied,
            total_available_for_month,
            balance_after_payment,
            credit_amount,
            payment_status,
        ) = calculate_month_payment_totals(
            db,
            payment.tenant_id,
            payment.unit_id,
            unit.rent_amount,
            payment.month_paid_for,
            exclude_payment_id=payment.id,
            extra_amount_paid=payment.amount_paid,
        )
        validate_zero_payment(payment.amount_paid, previous_credit_applied)
        save_month_totals_on_payment(
            payment,
            total_paid_for_month,
            previous_credit_applied,
            total_available_for_month,
            balance_after_payment,
            credit_amount,
            payment_status,
        )

    db.commit()
    db.refresh(payment)
    return add_payment_totals_to_response(db, payment)


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
