from app.routes.auth import router as auth_router
from app.routes.payments import router as payments_router
from app.routes.properties import router as properties_router
from app.routes.tenants import router as tenants_router
from app.routes.units import router as units_router


__all__ = [
    "auth_router",
    "payments_router",
    "properties_router",
    "tenants_router",
    "units_router",
]
