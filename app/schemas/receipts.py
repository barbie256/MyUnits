from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


PaymentStatus = Literal["paid", "partial", "overdue"]


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_number: str
    payment_id: int
    tenant_id: int
    tenant_name: str
    property_name: str
    unit_name: str
    amount_paid: Decimal
    payment_method: str
    payment_date: date
    month_paid_for: str
    total_available_for_month: Decimal
    balance_after_payment: Decimal
    credit_amount: Decimal
    payment_status: PaymentStatus
    recorded_by: int
    created_at: datetime
