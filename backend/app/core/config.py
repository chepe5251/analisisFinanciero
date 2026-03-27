"""
Configuración centralizada de la aplicación.
Todas las variables de entorno se leen desde aquí.
Supuesto: si no existe .env, se usan los valores por defecto (desarrollo local).
"""
from pydantic_settings import BaseSettings
from typing import List
import os
import secrets


class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str = "postgresql://user:password@localhost/reconciliation_db"

    # Directorio de archivos subidos
    UPLOAD_DIR: str = "uploads"

    # Límite de tamaño de archivo (MB)
    MAX_FILE_SIZE_MB: int = 50

    # Extensiones permitidas
    ALLOWED_EXTENSIONS: List[str] = [".csv", ".xlsx"]

    # Orígenes permitidos para CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Tolerancia de diferencia de monto para considerar un match exacto
    AMOUNT_TOLERANCE: float = 0.01

    # Umbral de similitud de nombre (0.0 a 1.0)
    NAME_SIMILARITY_THRESHOLD: float = 0.80

    # ── Autenticación ──────────────────────────────────────────────────
    # Clave secreta para firmar los JWT. En producción, usa una clave larga y aleatoria.
    SECRET_KEY: str = secrets.token_hex(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8

    # Credenciales del administrador por defecto (solo se crean si no hay usuarios)
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@reconcilaapp.local"
    DEFAULT_ADMIN_PASSWORD: str = "Admin1234!"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Crear directorio de uploads si no existe
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
