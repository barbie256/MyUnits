from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PaymentStatus = Literal["paid", "partial", "overdue"]


class PaymentCreate(BaseModel):
    amount_paid: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    payment_method: str = Field(min_length=1, max_length=80)
    payment_date: date
    month_paid_for: str = Field(min_length=1, max_length=20)


class PaymentUpdate(BaseModel):
    amount_paid: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    payment_method: str | None = Field(default=None, min_length=1, max_length=80)
    payment_date: date | None = None
    month_paid_for: str | None = Field(default=None, min_length=1, max_length=20)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    unit_id: int
    amount_paid: Decimal
    payment_method: str
    payment_date: date
    month_paid_for: str
    total_paid_for_month: Decimal
    previous_credit_applied: Decimal
    total_available_for_month: Decimal
    balance_after_payment: Decimal
    credit_amount: Decimal
    payment_status: PaymentStatus
    recorded_by: int
    created_at: datetime
