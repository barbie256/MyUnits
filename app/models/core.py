from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('landlord', 'manager', 'caretaker')",
            name="check_user_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    properties: Mapped[list["Property"]] = relationship(back_populates="owner")
    recorded_payments: Mapped[list["Payment"]] = relationship(back_populates="recorder")


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        CheckConstraint(
            "property_type IN ('apartment', 'hostel', 'shops', 'residential')",
            name="check_property_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    property_name: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    property_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship(back_populates="properties")
    units: Mapped[list["Unit"]] = relationship(back_populates="property")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="property")
    maintenance_requests: Mapped[list["MaintenanceRequest"]] = relationship(
        back_populates="property"
    )


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (
        CheckConstraint(
            "status IN ('vacant', 'occupied', 'reserved')",
            name="check_unit_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False)
    unit_name: Mapped[str] = mapped_column(String(80), nullable=False)
    rent_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="vacant")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    property: Mapped["Property"] = relationship(back_populates="units")
    tenants: Mapped[list["Tenant"]] = relationship(back_populates="unit")
    payments: Mapped[list["Payment"]] = relationship(back_populates="unit")
    maintenance_requests: Mapped[list["MaintenanceRequest"]] = relationship(
        back_populates="unit"
    )


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'moved_out')",
            name="check_tenant_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    national_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    move_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    rent_due_day: Mapped[int] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    unit: Mapped["Unit"] = relationship(back_populates="tenants")
    payments: Mapped[list["Payment"]] = relationship(back_populates="tenant")
    maintenance_requests: Mapped[list["MaintenanceRequest"]] = relationship(
        back_populates="tenant"
    )


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "payment_status IN ('paid', 'partial', 'overdue')",
            name="check_payment_status",
        ),
        CheckConstraint("credit_amount >= 0", name="check_credit_amount_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(80), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    month_paid_for: Mapped[str] = mapped_column(String(20), nullable=False)
    balance_after_payment: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0"),
    )
    payment_status: Mapped[str] = mapped_column(String(30), nullable=False)
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="payments")
    unit: Mapped["Unit"] = relationship(back_populates="payments")
    recorder: Mapped["User"] = relationship(back_populates="recorded_payments")
    receipt: Mapped["Receipt | None"] = relationship(back_populates="payment")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False)
    expense_title: Mapped[str] = mapped_column(String(150), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    property: Mapped["Property"] = relationship(back_populates="expenses")


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="check_maintenance_priority",
        ),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'fixed')",
            name="check_maintenance_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    issue_title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(30), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    property: Mapped["Property"] = relationship(back_populates="maintenance_requests")
    unit: Mapped["Unit"] = relationship(back_populates="maintenance_requests")
    tenant: Mapped["Tenant"] = relationship(back_populates="maintenance_requests")


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id"),
        unique=True,
        nullable=False,
    )
    receipt_number: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        index=True,
        nullable=False,
    )
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    payment: Mapped["Payment"] = relationship(back_populates="receipt")
