"""
Punto de entrada de la aplicación FastAPI.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.api import api_router

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    """
    Ejecuta las migraciones de Alembic al arrancar.
    Reemplaza el create_all() directo para usar migraciones versionadas.
    En desarrollo sin alembic configurado, hace fallback a create_all().
    """
    try:
        from alembic.config import Config
        from alembic import command
        import os

        alembic_cfg = Config("alembic.ini")
        # Asegurar que DATABASE_URL del entorno se pase a Alembic
        db_url = settings.DATABASE_URL
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(alembic_cfg, "head")
        logger.info("Migraciones Alembic aplicadas exitosamente.")
    except Exception as exc:
        logger.warning(
            "No se pudieron aplicar migraciones Alembic (%s). "
            "Usando create_all() como fallback.",
            exc,
        )
        from app.core.database import create_tables
        create_tables()


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
    """Ejecuta migraciones y crea el usuario admin inicial al arrancar."""
    _run_migrations()
    _seed_admin()
    yield


app = FastAPI(
    title="ReconcilaApp — Financial Management API",
    description=(
        "Sistema de contabilidad y gestión financiera empresarial. "
        "Incluye conciliación de nóminas, contabilidad general, presupuestos y facturación."
    ),
    version="2.0.0",
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
    return {
        "message": "ReconcilaApp Financial Management API",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
