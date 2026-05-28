from fastapi import FastAPI

from app import models  # noqa: F401
from app.config import settings
from app.db import Base, engine
from app.routes import auth_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
)

app.include_router(auth_router)


@app.on_event("startup")
def create_database_tables() -> None:
    # create_all checks Base metadata and creates any missing tables.
    # Existing tables are left alone, so this is simple startup setup.
    Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root() -> str:
    return "MyUnits backend is running"
