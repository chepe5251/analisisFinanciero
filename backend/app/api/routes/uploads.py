"""
Endpoints de gestión de archivos subidos.
Responsabilidad: validar, guardar y disparar el procesamiento de archivos.
"""
import os
import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.schemas.schemas import UploadOut, UploadResponse, UploadCreate
from app.repositories.repositories import UploadRepository
from app.services.reconciliation_service import ReconciliationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/uploads", tags=["uploads"])

MAX_FILE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers de validación y guardado
# ---------------------------------------------------------------------------

def _validate_extension(filename: str) -> None:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Extensión '{ext}' no permitida. "
                f"Formatos aceptados: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            ),
        )


async def _read_and_validate_file(file: UploadFile) -> bytes:
    """
    Lee el archivo completo en memoria para:
    1. Verificar que no está vacío.
    2. Verificar que no supera el límite de tamaño.
    """
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"El archivo supera el límite de {settings.MAX_FILE_SIZE_MB} MB "
                f"({len(content) / 1_048_576:.1f} MB recibidos)."
            ),
        )
    return content


def _save_to_disk(original_filename: str, content: bytes) -> str:
    """
    Guarda el contenido en disco con un nombre único para evitar colisiones.
    Formato: <uuid>_<nombre_sanitizado>
    Retorna la ruta absoluta del archivo guardado.
    """
    safe_name = (original_filename or "upload").replace(" ", "_")
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/template", response_model=UploadResponse, summary="Subir plantilla de personal")
async def upload_template(
    file: UploadFile = File(..., description="Archivo CSV o Excel con la plantilla de personal"),
    db: Session = Depends(get_db),
):
    """
    Sube y procesa la plantilla principal de personal.

    **Columnas requeridas:** `employee_id`, `full_name`, `bank_name`, `account_number`, `expected_amount`

    **Columnas opcionales:** `identification`, `currency`

    El sistema acepta variantes en nombres de columna (ej. `nombre`, `banco`, `monto_esperado`).
    """
    _validate_extension(file.filename or "")
    content = await _read_and_validate_file(file)
    file_path = _save_to_disk(file.filename or "template.csv", content)

    upload_repo = UploadRepository(db)
    upload = upload_repo.create(UploadCreate(file_name=file.filename, file_type="template"))

    service = ReconciliationService(db)
    try:
        records, stats = service.process_employee_template(upload.id, file_path)
        upload_repo.update_status(
            upload.id,
            "completed",
            total_rows=stats.total,
            processed_rows=stats.processed,
            error_rows=stats.errors,
        )
        message = f"Plantilla procesada: {stats.summary_message()}"
    except ValueError as e:
        upload_repo.update_status(upload.id, "failed", error_message=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        upload_repo.update_status(upload.id, "failed", error_message=str(e))
        logger.exception("Error inesperado procesando plantilla upload_id=%d", upload.id)
        raise HTTPException(status_code=500, detail=f"Error procesando plantilla: {e}")

    db.refresh(upload)
    return UploadResponse(upload=UploadOut.model_validate(upload), message=message)


@router.post("/bank-report", response_model=UploadResponse, summary="Subir reporte bancario")
async def upload_bank_report(
    file: UploadFile = File(..., description="Archivo CSV o Excel del banco"),
    bank_name: str = Form(
        ...,
        description="Nombre del banco (ej: Banco_A). Debe coincidir con el formato del archivo.",
    ),
    db: Session = Depends(get_db),
):
    """
    Sube y procesa un reporte bancario.

    El parámetro `bank_name` se usa para seleccionar el mapeo de columnas.
    Bancos soportados con mapeo automático: `Banco_A`, `Banco_B`, `Banco_C`.
    Para otros bancos, el sistema intenta detectar columnas automáticamente.
    """
    _validate_extension(file.filename or "")

    bank_name = bank_name.strip()
    if not bank_name:
        raise HTTPException(status_code=400, detail="El campo bank_name no puede estar vacío.")

    content = await _read_and_validate_file(file)
    file_path = _save_to_disk(file.filename or "report.csv", content)

    upload_repo = UploadRepository(db)
    upload = upload_repo.create(
        UploadCreate(file_name=file.filename, file_type="bank_report", source_bank=bank_name)
    )

    service = ReconciliationService(db)
    try:
        records, stats = service.process_bank_transactions(upload.id, file_path, bank_name)
        upload_repo.update_status(
            upload.id,
            "completed",
            total_rows=stats.total,
            processed_rows=stats.processed,
            error_rows=stats.errors,
        )
        message = f"Reporte de {bank_name} procesado: {stats.summary_message()}"
    except ValueError as e:
        upload_repo.update_status(upload.id, "failed", error_message=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        upload_repo.update_status(upload.id, "failed", error_message=str(e))
        logger.exception("Error inesperado procesando reporte bank=%s upload_id=%d", bank_name, upload.id)
        raise HTTPException(status_code=500, detail=f"Error procesando reporte bancario: {e}")

    db.refresh(upload)
    return UploadResponse(
        upload=UploadOut.model_validate(upload),
        message=message,
    )


@router.get("", response_model=List[UploadOut], summary="Listar todos los archivos subidos")
def list_uploads(
    file_type: Optional[str] = Query(
        None, description="Filtrar por tipo: template | bank_report"
    ),
    db: Session = Depends(get_db),
):
    """Retorna todos los archivos subidos, ordenados por fecha descendente."""
    repo = UploadRepository(db)
    return repo.get_all(file_type=file_type)


@router.get("/stats/overview", summary="Resumen rápido de uploads para el dashboard")
def get_upload_stats(db: Session = Depends(get_db)):
    """
    Retorna conteos de uploads por tipo y estado.
    Usado por el dashboard para mostrar si hay datos disponibles.
    """
    repo = UploadRepository(db)
    all_uploads = repo.get_all()
    templates = [u for u in all_uploads if u.file_type == "template" and u.status == "completed"]
    bank_reports = [u for u in all_uploads if u.file_type == "bank_report" and u.status == "completed"]
    return {
        "total_uploads": len(all_uploads),
        "templates_completed": len(templates),
        "bank_reports_completed": len(bank_reports),
        "banks_available": list({u.source_bank for u in bank_reports if u.source_bank}),
        "latest_template": (
            {"id": templates[0].id, "file_name": templates[0].file_name, "rows": templates[0].processed_rows}
            if templates else None
        ),
    }


@router.get("/{upload_id}", response_model=UploadOut, summary="Detalle de un archivo")
def get_upload(upload_id: int, db: Session = Depends(get_db)):
    repo = UploadRepository(db)
    record = repo.get_by_id(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Upload con id={upload_id} no encontrado.")
    return record
