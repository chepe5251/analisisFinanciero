"""
Configuración de la base de datos SQLAlchemy.
Base es la clase padre de todos los modelos.
Se importa desde aquí para evitar bases duplicadas.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from .config import settings

# Base única para todos los modelos — los modelos importan esta
Base = declarative_base()

engine = create_engine(
    settings.DATABASE_URL,
    # pool_pre_ping verifica la conexión antes de usarla (evita conexiones muertas)
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency de FastAPI para inyectar sesión de base de datos.
    Garantiza que la sesión se cierre al terminar el request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Crea todas las tablas en la base de datos.
    Se llama en el startup de la aplicación.
    Supuesto: en producción se usaría Alembic para migraciones.
    """
    # Importar modelos para que SQLAlchemy los registre en Base.metadata
    from app.models import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
