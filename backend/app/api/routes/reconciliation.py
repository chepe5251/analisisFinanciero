"""
Endpoints de conciliación.

POST /run            →  ejecuta la conciliación
GET  /summary        →  KPIs del dashboard
GET  /bank-summary   →  resumen por banco
GET  /results        →  resultados con filtros y paginación
GET  /inconsistencies →  solo registros que requieren revisión
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import (
    ReconciliationRunRequest, ReconciliationRunResponse,
    ReconciliationSummary, BankSummary, PaginatedResults, ReconciliationResultOut,
)
from app.repositories.repositories import ReconciliationResultRepository
from app.services.reconciliation_service import ReconciliationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


@router.post("/run", response_model=ReconciliationRunResponse, summary="Ejecutar conciliación")
def run_reconciliation(
    request: ReconciliationRunRequest,
    db: Session = Depends(get_db),
):
    """
    Ejecuta la conciliación cruzando la plantilla de personal contra los reportes bancarios.

    - `template_upload_id`: ID del upload de tipo `template`
    - `bank_upload_ids`: lista de IDs de uploads tipo `bank_report`

    ⚠️ Limpia los resultados anteriores antes de ejecutar.
    """
    service = ReconciliationService(db)
    try:
        result = service.run_reconciliation(request)
        return ReconciliationRunResponse(
            summary=result.summary,
            message="Conciliación completada exitosamente",
            batch_id=result.batch_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Error inesperado en conciliación")
        raise HTTPException(status_code=500, detail=f"Error interno en conciliación: {e}")


@router.get("/summary", response_model=ReconciliationSummary, summary="KPIs del dashboard")
def get_summary(db: Session = Depends(get_db)):
    """Retorna los indicadores agregados de la última corrida de conciliación."""
    repo = ReconciliationResultRepository(db)
    data = repo.get_summary()
    return ReconciliationSummary(**data)


@router.get("/bank-summary", response_model=List[BankSummary], summary="Resumen por banco")
def get_bank_summary(db: Session = Depends(get_db)):
    """Retorna el conteo de transacciones agrupado por banco."""
    repo = ReconciliationResultRepository(db)
    return repo.get_bank_summary()


@router.get(
    "/results",
    response_model=PaginatedResults,
    summary="Resultados con filtros y paginación",
)
def get_results(
    status: Optional[str] = Query(
        None,
        description="Estado: matched | difference | missing | extra | duplicate | pending",
    ),
    bank_name: Optional[str] = Query(None, description="Filtrar por banco (parcial)"),
    employee_name: Optional[str] = Query(None, description="Filtrar por nombre de empleado (parcial)"),
    min_amount: Optional[float] = Query(None, description="Monto mínimo"),
    max_amount: Optional[float] = Query(None, description="Monto máximo"),
    page: int = Query(1, ge=1, description="Página (empieza en 1)"),
    page_size: int = Query(50, ge=1, le=200, description="Resultados por página"),
    db: Session = Depends(get_db),
):
    """Retorna resultados de la conciliación con filtros y paginación."""
    repo = ReconciliationResultRepository(db)
    offset = (page - 1) * page_size
    items, total = repo.get_filtered(
        status=status,
        bank_name=bank_name,
        employee_name=employee_name,
        min_amount=min_amount,
        max_amount=max_amount,
        offset=offset,
        limit=page_size,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResults(
        items=[ReconciliationResultOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/inconsistencies",
    response_model=List[ReconciliationResultOut],
    summary="Solo inconsistencias",
)
def get_inconsistencies(db: Session = Depends(get_db)):
    """
    Retorna únicamente los registros que requieren revisión del operador:
    difference, missing, extra, duplicate, pending.
    """
    repo = ReconciliationResultRepository(db)
    items = repo.get_inconsistencies()
    return [ReconciliationResultOut.model_validate(i) for i in items]
