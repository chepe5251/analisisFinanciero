"""
Endpoints de presupuestos.

POST   /budgets                    Crear presupuesto
GET    /budgets                    Listar presupuestos
GET    /budgets/{id}               Detalle de presupuesto
POST   /budgets/{id}/approve       Aprobar presupuesto
GET    /budgets/{id}/execution     Ver ejecución vs. planificado
GET    /budgets/{id}/variance      Reporte de varianza
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.models import User
from app.schemas.schemas import BudgetCreate, BudgetOut, BudgetExecutionReport
from app.services.budget_service import BudgetService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/budgets", tags=["budgets"])

_view = require_permission("budgets", "view")
_create = require_permission("budgets", "create")
_approve = require_permission("budgets", "approve")


@router.post("", response_model=BudgetOut, status_code=201)
def create_budget(
    body: BudgetCreate,
    current_user: User = Depends(_create),
    db: Session = Depends(get_db),
):
    """Crea un presupuesto en estado borrador."""
    svc = BudgetService(db)
    budget = svc.create_budget(body, created_by_id=current_user.id)
    return BudgetOut.model_validate(budget)


@router.get("", response_model=List[BudgetOut])
def list_budgets(
    company_id: Optional[int] = Query(None),
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """Lista todos los presupuestos con su estado."""
    svc = BudgetService(db)
    budgets = svc.get_budgets(company_id)
    return [BudgetOut.model_validate(b) for b in budgets]


@router.get("/{budget_id}", response_model=BudgetOut)
def get_budget(
    budget_id: int,
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    svc = BudgetService(db)
    return BudgetOut.model_validate(svc.get_budget(budget_id))


@router.post("/{budget_id}/approve", response_model=BudgetOut)
def approve_budget(
    budget_id: int,
    current_user: User = Depends(_approve),
    db: Session = Depends(get_db),
):
    """
    Aprueba el presupuesto. Un presupuesto aprobado no puede modificarse;
    para revisarlo, crea uno nuevo referenciando al anterior.
    """
    svc = BudgetService(db)
    budget = svc.approve_budget(budget_id, approved_by_id=current_user.id)
    return BudgetOut.model_validate(budget)


@router.get("/{budget_id}/execution", response_model=BudgetExecutionReport)
def get_budget_execution(
    budget_id: int,
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """
    Compara el monto planificado vs. el ejecutado (asientos del período)
    calculando varianza y porcentaje de ejecución por cuenta.
    """
    svc = BudgetService(db)
    return svc.get_execution_report(budget_id)


@router.get("/{budget_id}/variance", response_model=BudgetExecutionReport)
def get_budget_variance(
    budget_id: int,
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """Alias de /execution — reporte de varianza por cuenta."""
    svc = BudgetService(db)
    return svc.get_execution_report(budget_id)
