from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app import models  # noqa: F401
from app.constants import (
    DEFAULT_CURRENCY,
    SUPPORTED_CURRENCIES,
    SUPPORTED_ID_DOCUMENT_TYPES,
    SUPPORTED_PROPERTY_TYPES,
    sql_allowed_values,
)
from app.config import settings
from app.db import Base, engine
from app.routes import (
    auth_router,
    dashboard_router,
    maintenance_router,
    payments_router,
    properties_router,
    receipts_router,
    tenants_router,
    units_router,
)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
)

allowed_origins = [
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:19006",
    "http://127.0.0.1:19006",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(properties_router)
app.include_router(units_router)
app.include_router(tenants_router)
app.include_router(payments_router)
app.include_router(receipts_router)
app.include_router(maintenance_router)
app.include_router(dashboard_router)


@app.on_event("startup")
def create_database_tables() -> None:
    # create_all checks Base metadata and creates any missing tables.
    # Existing tables are left alone, so this is simple startup setup.
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    add_missing_payment_columns(inspector)
    add_missing_receipt_columns(inspector)
    add_missing_user_columns(inspector)
    add_missing_tenant_identity_columns(inspector)
    update_allowed_value_constraints()
    allow_maintenance_without_tenant(inspector)


def add_missing_payment_columns(inspector: object) -> None:
    if "payments" not in inspector.get_table_names():
        return

    payment_columns = [column["name"] for column in inspector.get_columns("payments")]
    missing_payment_status = "payment_status" not in payment_columns
    missing_credit_amount = "credit_amount" not in payment_columns

    if not missing_payment_status and not missing_credit_amount:
        return

    with engine.begin() as connection:
        if missing_payment_status:
            connection.execute(
                text(
                    "ALTER TABLE payments "
                    "ADD COLUMN payment_status VARCHAR(30) NOT NULL DEFAULT 'partial'"
                )
            )

        if missing_credit_amount:
            connection.execute(
                text(
                    "ALTER TABLE payments "
                    "ADD COLUMN credit_amount NUMERIC(12, 2) NOT NULL DEFAULT 0"
                )
            )

        connection.execute(
            text(
                "UPDATE payments "
                "SET credit_amount = 0 "
                "WHERE credit_amount < 0"
            )
        )


def add_missing_receipt_columns(inspector: object) -> None:
    if "receipts" not in inspector.get_table_names():
        return

    receipt_columns = [column["name"] for column in inspector.get_columns("receipts")]
    columns_to_add = {
        "tenant_id": "INTEGER",
        "tenant_name": "VARCHAR(150)",
        "property_name": "VARCHAR(150)",
        "unit_name": "VARCHAR(80)",
        "amount_paid": "NUMERIC(12, 2)",
        "payment_method": "VARCHAR(80)",
        "payment_date": "DATE",
        "month_paid_for": "VARCHAR(20)",
        "total_available_for_month": "NUMERIC(12, 2)",
        "balance_after_payment": "NUMERIC(12, 2)",
        "credit_amount": "NUMERIC(12, 2)",
        "payment_status": "VARCHAR(30)",
        "recorded_by": "INTEGER",
    }

    missing_columns = {
        name: column_type
        for name, column_type in columns_to_add.items()
        if name not in receipt_columns
    }
    if not missing_columns:
        return

    with engine.begin() as connection:
        for name, column_type in missing_columns.items():
            connection.execute(
                text(f"ALTER TABLE receipts ADD COLUMN {name} {column_type}")
            )


def add_missing_user_columns(inspector: object) -> None:
    if "users" not in inspector.get_table_names():
        return

    user_columns = [column["name"] for column in inspector.get_columns("users")]
    if "currency" in user_columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE users "
                f"ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT '{DEFAULT_CURRENCY}'"
            )
        )


def add_missing_tenant_identity_columns(inspector: object) -> None:
    if "tenants" not in inspector.get_table_names():
        return

    tenant_columns = [column["name"] for column in inspector.get_columns("tenants")]
    columns_to_add = {
        "nationality": "VARCHAR(80)",
        "id_document_type": "VARCHAR(30)",
        "id_document_number": "VARCHAR(80)",
        "id_document_image_url": "VARCHAR(500)",
    }

    missing_columns = {
        name: column_type
        for name, column_type in columns_to_add.items()
        if name not in tenant_columns
    }
    if not missing_columns:
        return

    with engine.begin() as connection:
        for name, column_type in missing_columns.items():
            connection.execute(
                text(f"ALTER TABLE tenants ADD COLUMN {name} {column_type}")
            )

        if "national_id" in tenant_columns:
            connection.execute(
                text(
                    "UPDATE tenants "
                    "SET id_document_type = 'national_id', "
                    "id_document_number = national_id "
                    "WHERE national_id IS NOT NULL "
                    "AND id_document_number IS NULL"
                )
            )


def update_allowed_value_constraints() -> None:
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_currency")
        )
        connection.execute(
            text(
                "ALTER TABLE users "
                "ADD CONSTRAINT check_user_currency "
                f"CHECK (currency IN ({sql_allowed_values(SUPPORTED_CURRENCIES)}))"
            )
        )

        connection.execute(
            text("ALTER TABLE properties DROP CONSTRAINT IF EXISTS check_property_type")
        )
        connection.execute(
            text(
                "ALTER TABLE properties "
                "ADD CONSTRAINT check_property_type "
                f"CHECK (property_type IN ({sql_allowed_values(SUPPORTED_PROPERTY_TYPES)}))"
            )
        )

        connection.execute(
            text(
                "ALTER TABLE tenants "
                "DROP CONSTRAINT IF EXISTS check_tenant_id_document_type"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE tenants "
                "ADD CONSTRAINT check_tenant_id_document_type "
                "CHECK (id_document_type IS NULL OR "
                f"id_document_type IN ({sql_allowed_values(SUPPORTED_ID_DOCUMENT_TYPES)}))"
            )
        )


def allow_maintenance_without_tenant(inspector: object) -> None:
    if "maintenance_requests" not in inspector.get_table_names():
        return

    maintenance_columns = inspector.get_columns("maintenance_requests")
    tenant_column = next(
        (column for column in maintenance_columns if column["name"] == "tenant_id"),
        None,
    )
    if tenant_column is None or tenant_column["nullable"]:
        return

    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE maintenance_requests ALTER COLUMN tenant_id DROP NOT NULL")
        )


@app.get("/")
def read_root() -> str:
    return "MyUnits backend is running"
