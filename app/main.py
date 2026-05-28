from fastapi import FastAPI

from app import models  # noqa: F401
from app.config import settings
from app.routes import auth_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
)

app.include_router(auth_router)


@app.get("/")
def read_root() -> str:
    return "MyUnits backend is running"
