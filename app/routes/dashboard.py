from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Payment, Property, Tenant, Unit, User
from app.routes.auth import get_current_user
from app.schemas.dashboard import DashboardSummaryResponse, RecentPaymentResponse


router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def money_total(value: object) -> Decimal:
    if value is None:
        return Decimal("0")

    return Decimal(value)


def get_current_month_labels() -> list[str]:
    today = date.today()
    month_name = today.strftime("%B")
    short_month_name = today.strftime("%b")

    return [
        today.strftime("%Y-%m").lower(),
        f"{month_name} {today.year}".lower(),
        f"{short_month_name} {today.year}".lower(),
        month_name.lower(),
        short_month_name.lower(),
    ]


def count_landlord_properties(db: Session, landlord_id: int) -> int:
    return db.scalar(
        select(func.count(Property.id)).where(Property.owner_id == landlord_id)
    ) or 0


def count_landlord_units(db: Session, landlord_id: int, status: str | None = None) -> int:
    query = (
        select(func.count(Unit.id))
        .join(Property, Unit.property_id == Property.id)
        .where(Property.owner_id == landlord_id)
    )

    if status is not None:
        query = query.where(Unit.status == status)

    return db.scalar(query) or 0


def count_active_tenants(db: Session, landlord_id: int) -> int:
    return db.scalar(
        select(func.count(Tenant.id))
        .join(Unit, Tenant.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(
            Property.owner_id == landlord_id,
            Tenant.status == "active",
        )
    ) or 0


def get_expected_monthly_rent(db: Session, landlord_id: int) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(Unit.rent_amount), 0))
        .join(Property, Unit.property_id == Property.id)
        .where(
            Property.owner_id == landlord_id,
            Unit.status == "occupied",
        )
    )

    return money_total(total)


def get_current_month_payments(db: Session, landlord_id: int) -> list[Payment]:
    return list(
        db.scalars(
            select(Payment)
            .join(Unit, Payment.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(
                Property.owner_id == landlord_id,
                func.lower(Payment.month_paid_for).in_(get_current_month_labels()),
            )
            .order_by(Payment.payment_date.asc(), Payment.created_at.asc())
        )
    )


def get_month_balance_totals(
    db: Session,
    landlord_id: int,
    payments: list[Payment],
) -> tuple[Decimal, Decimal]:
    latest_payments_by_tenant: dict[int, Payment] = {}

    for payment in payments:
        latest_payments_by_tenant[payment.tenant_id] = payment

    outstanding_total = Decimal("0")
    credit_total = Decimal("0")
    active_tenants = db.execute(
        select(Tenant, Unit)
        .join(Unit, Tenant.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(
            Property.owner_id == landlord_id,
            Tenant.status == "active",
        )
    ).all()

    for tenant, unit in active_tenants:
        latest_payment = latest_payments_by_tenant.get(tenant.id)
        if latest_payment is None:
            outstanding_total += money_total(unit.rent_amount)
        else:
            outstanding_total += money_total(latest_payment.balance_after_payment)
            credit_total += money_total(latest_payment.credit_amount)

    return outstanding_total, credit_total


def get_recent_payments(db: Session, landlord_id: int) -> list[RecentPaymentResponse]:
    payment_rows = db.execute(
        select(Payment, Tenant, Unit, Property)
        .join(Tenant, Payment.tenant_id == Tenant.id)
        .join(Unit, Payment.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Property.owner_id == landlord_id)
        .order_by(Payment.payment_date.desc(), Payment.created_at.desc())
        .limit(5)
    ).all()

    recent_payments = []
    for payment, tenant, unit, property_item in payment_rows:
        recent_payments.append(
            RecentPaymentResponse(
                tenant_name=tenant.full_name,
                property_name=property_item.property_name,
                unit_name=unit.unit_name,
                amount_paid=payment.amount_paid,
                payment_method=payment.payment_method,
                payment_date=payment.payment_date,
                payment_status=payment.payment_status,
            )
        )

    return recent_payments


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get dashboard summary",
)
def read_dashboard_summary(
    db: DbSession,
    current_user: CurrentUser,
) -> DashboardSummaryResponse:
    current_month_payments = get_current_month_payments(db, current_user.id)
    collected_this_month = sum(
        (money_total(payment.amount_paid) for payment in current_month_payments),
        Decimal("0"),
    )
    outstanding_this_month, tenant_credit_this_month = get_month_balance_totals(
        db,
        current_user.id,
        current_month_payments,
    )

    return DashboardSummaryResponse(
        total_properties=count_landlord_properties(db, current_user.id),
        total_units=count_landlord_units(db, current_user.id),
        occupied_units=count_landlord_units(db, current_user.id, "occupied"),
        vacant_units=count_landlord_units(db, current_user.id, "vacant"),
        reserved_units=count_landlord_units(db, current_user.id, "reserved"),
        total_active_tenants=count_active_tenants(db, current_user.id),
        expected_monthly_rent=get_expected_monthly_rent(db, current_user.id),
        collected_this_month=collected_this_month,
        outstanding_this_month=outstanding_this_month,
        tenant_credit_this_month=tenant_credit_this_month,
        recent_payments=get_recent_payments(db, current_user.id),
    )
