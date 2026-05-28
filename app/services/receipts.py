from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Payment, Property, Receipt, Tenant, Unit


def generate_receipt_number(db: Session, payment: Payment) -> str:
    year = payment.payment_date.year
    prefix = f"MYU-{year}-"
    receipt_numbers = db.scalars(
        select(Receipt.receipt_number).where(Receipt.receipt_number.like(f"{prefix}%"))
    )

    highest_sequence = 0
    for receipt_number in receipt_numbers:
        try:
            sequence = int(receipt_number.replace(prefix, "", 1))
        except ValueError:
            continue

        highest_sequence = max(highest_sequence, sequence)

    return f"{prefix}{highest_sequence + 1:04d}"


def add_payment_details_to_receipt(
    receipt: Receipt,
    payment: Payment,
    tenant: Tenant,
    unit: Unit,
    property_item: Property,
    total_available_for_month: Decimal,
) -> Receipt:
    receipt.tenant_id = tenant.id
    receipt.tenant_name = tenant.full_name
    receipt.property_name = property_item.property_name
    receipt.unit_name = unit.unit_name
    receipt.amount_paid = payment.amount_paid
    receipt.payment_method = payment.payment_method
    receipt.payment_date = payment.payment_date
    receipt.month_paid_for = payment.month_paid_for
    receipt.total_available_for_month = total_available_for_month
    receipt.balance_after_payment = payment.balance_after_payment
    receipt.credit_amount = payment.credit_amount
    receipt.payment_status = payment.payment_status
    receipt.recorded_by = payment.recorded_by
    return receipt


def get_payment_details_for_receipt(
    db: Session,
    payment: Payment,
) -> tuple[Tenant, Unit, Property]:
    tenant = db.get(Tenant, payment.tenant_id)
    unit = db.get(Unit, payment.unit_id)
    if tenant is None or unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    property_item = db.get(Property, unit.property_id)
    if property_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return tenant, unit, property_item


def get_total_available_from_saved_payment(payment: Payment, unit: Unit) -> Decimal:
    return (
        Decimal(unit.rent_amount)
        - Decimal(payment.balance_after_payment)
        + Decimal(payment.credit_amount)
    )


def create_receipt_for_payment(
    db: Session,
    payment: Payment,
    total_available_for_month: Decimal | None = None,
) -> Receipt:
    tenant, unit, property_item = get_payment_details_for_receipt(db, payment)
    if total_available_for_month is None:
        total_available_for_month = get_total_available_from_saved_payment(payment, unit)

    existing_receipt = db.scalar(
        select(Receipt).where(Receipt.payment_id == payment.id)
    )
    if existing_receipt is not None:
        return add_payment_details_to_receipt(
            existing_receipt,
            payment,
            tenant,
            unit,
            property_item,
            total_available_for_month,
        )

    receipt = Receipt(
        receipt_number=generate_receipt_number(db, payment),
        payment_id=payment.id,
        tenant_id=tenant.id,
        tenant_name=tenant.full_name,
        property_name=property_item.property_name,
        unit_name=unit.unit_name,
        amount_paid=payment.amount_paid,
        payment_method=payment.payment_method,
        payment_date=payment.payment_date,
        month_paid_for=payment.month_paid_for,
        total_available_for_month=total_available_for_month,
        balance_after_payment=payment.balance_after_payment,
        credit_amount=payment.credit_amount,
        payment_status=payment.payment_status,
        recorded_by=payment.recorded_by,
    )

    db.add(receipt)
    return receipt
