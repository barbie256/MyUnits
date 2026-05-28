import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "MyUnits")
    API_VERSION: str = os.getenv("API_VERSION", "0.1.0")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/myunits",
    )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )


settings = Settings()
