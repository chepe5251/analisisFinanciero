"""
Punto de entrada de la aplicación FastAPI.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_tables, SessionLocal
from app.api import api_router

logger = logging.getLogger(__name__)


def _seed_admin() -> None:
    """
    Crea el usuario admin por defecto si no existe ningún usuario en la BD.
    Las credenciales se leen de settings (DEFAULT_ADMIN_*).
    """
    from app.repositories.repositories import UserRepository
    from app.core.security import hash_password

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        if repo.count() > 0:
            return

        repo.create(
            username=settings.DEFAULT_ADMIN_USERNAME,
            email=settings.DEFAULT_ADMIN_EMAIL,
            hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            full_name="Administrador",
            role="admin",
            is_active=True,
        )
        logger.warning(
            "Usuario admin creado con credenciales por defecto. "
            "Cámbia la contraseña en la primera sesión. "
            "Usuario: %s | Contraseña: %s",
            settings.DEFAULT_ADMIN_USERNAME,
            settings.DEFAULT_ADMIN_PASSWORD,
        )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea las tablas y el usuario admin inicial al arrancar."""
    create_tables()
    _seed_admin()
    yield


app = FastAPI(
    title="Financial Reconciliation API",
    description="API para conciliación financiera de pagos de personal",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/", tags=["health"])
def root():
    return {"message": "Financial Reconciliation API", "version": "1.0.0"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
