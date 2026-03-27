"""
Configuración centralizada de la aplicación.
Todas las variables de entorno se leen desde aquí.
Supuesto: si no existe .env, se usan los valores por defecto (desarrollo local).
"""
from pydantic_settings import BaseSettings
from typing import List
import os


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
    # (ej: 0.01 = diferencias de hasta 1 centavo se consideran iguales)
    AMOUNT_TOLERANCE: float = 0.01

    # Umbral de similitud de nombre (0.0 a 1.0) para match por nombre aproximado
    # Supuesto: nombres con 80% de similitud se consideran candidatos
    NAME_SIMILARITY_THRESHOLD: float = 0.80

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Crear directorio de uploads si no existe
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
