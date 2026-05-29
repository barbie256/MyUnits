from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


PaymentStatus = Literal["paid", "partial", "overdue"]


class RecentPaymentResponse(BaseModel):
    tenant_name: str
    property_name: str
    unit_name: str
    amount_paid: Decimal
    payment_method: str
    payment_date: date
    payment_status: PaymentStatus


class DashboardSummaryResponse(BaseModel):
    currency: str
    total_properties: int
    total_units: int
    occupied_units: int
    vacant_units: int
    reserved_units: int
    total_active_tenants: int
    expected_monthly_rent: Decimal
    collected_this_month: Decimal
    outstanding_this_month: Decimal
    tenant_credit_this_month: Decimal
    recent_payments: list[RecentPaymentResponse]
