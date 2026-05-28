from fastapi import FastAPI
from sqlalchemy import inspect, text

from app import models  # noqa: F401
from app.config import settings
from app.db import Base, engine
from app.routes import (
    auth_router,
    payments_router,
    properties_router,
    tenants_router,
    units_router,
)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
)

app.include_router(auth_router)
app.include_router(properties_router)
app.include_router(units_router)
app.include_router(tenants_router)
app.include_router(payments_router)


@app.on_event("startup")
def create_database_tables() -> None:
    # create_all checks Base metadata and creates any missing tables.
    # Existing tables are left alone, so this is simple startup setup.
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
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


@app.get("/")
def read_root() -> str:
    return "MyUnits backend is running"
