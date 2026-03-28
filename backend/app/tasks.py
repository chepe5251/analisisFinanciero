"""
Tareas Celery para procesamiento asíncrono de archivos grandes (> 500 filas).

Para archivos pequeños, el procesamiento sigue siendo síncrono en el endpoint.
Para archivos grandes, el endpoint retorna inmediatamente con upload_id y status=pending;
el frontend hace polling a GET /uploads/{id} para ver el progreso.
"""
import logging
from typing import List

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="tasks.process_upload_async")
def process_upload_async(
    self,
    upload_id: int,
    file_path: str,
    file_type: str,
    bank_name: str = "",
) -> dict:
    """
    Procesa un archivo subido de forma asíncrona.
    Actualiza el estado del Upload en la BD al terminar.
    """
    from app.core.database import SessionLocal
    from app.repositories.repositories import UploadRepository
    from app.services.reconciliation_service import ReconciliationService

    db = SessionLocal()
    upload_repo = UploadRepository(db)
    svc = ReconciliationService(db)

    try:
        upload_repo.update_status(upload_id, "processing")

        if file_type == "template":
            records, stats = svc.process_employee_template(upload_id, file_path)
        else:
            records, stats = svc.process_bank_transactions(upload_id, file_path, bank_name)

        upload_repo.update_status(
            upload_id,
            "completed",
            total_rows=stats.total,
            processed_rows=stats.processed,
            error_rows=stats.errors,
            error_message="; ".join(stats.error_details[:5]) if stats.error_details else None,
        )
        logger.info("Upload %d procesado: %s", upload_id, stats.summary_message())
        return {"upload_id": upload_id, "status": "completed", "processed": stats.processed}

    except Exception as exc:
        upload_repo.update_status(
            upload_id,
            "failed",
            error_message=str(exc)[:500],
        )
        logger.error("Error procesando upload %d: %s", upload_id, exc)
        raise self.retry(exc=exc, countdown=5)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, name="tasks.run_reconciliation_async")
def run_reconciliation_async(self, request_dict: dict) -> dict:
    """
    Ejecuta la conciliación de forma asíncrona.
    request_dict: {"template_upload_id": int, "bank_upload_ids": [int]}
    """
    from app.core.database import SessionLocal
    from app.schemas.schemas import ReconciliationRunRequest
    from app.services.reconciliation_service import ReconciliationService

    db = SessionLocal()
    try:
        request = ReconciliationRunRequest(**request_dict)
        svc = ReconciliationService(db)
        result = svc.run_reconciliation(request)
        return {
            "batch_id": result.batch_id,
            "total_processed": result.summary.total_processed,
            "total_matched": result.summary.total_matched,
        }
    except Exception as exc:
        logger.error("Error en conciliación asíncrona: %s", exc)
        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()
