"""
Endpoints de contabilidad general.

POST   /accounting/accounts              Crear cuenta
GET    /accounting/accounts              Listar plan de cuentas (árbol)
POST   /accounting/entries               Crear asiento (valida cuadre)
GET    /accounting/entries               Listar asientos con filtros
POST   /accounting/entries/{id}/post     Publicar asiento borrador
POST   /accounting/entries/{id}/void     Anular asiento publicado
GET    /accounting/ledger/{account_id}   Mayor de una cuenta
GET    /accounting/trial-balance         Balance de comprobación
GET    /accounting/fiscal-periods        Listar períodos fiscales
POST   /accounting/fiscal-periods        Crear período fiscal
POST   /accounting/fiscal-periods/{id}/close  Cerrar período
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.models import User
from app.schemas.schemas import (
    ChartOfAccountCreate, ChartOfAccountOut, ChartOfAccountTree,
    JournalEntryCreate, JournalEntryOut, JournalEntryLineOut,
    LedgerLine, TrialBalanceLine, FiscalPeriodOut, FiscalPeriodCreate,
)
from app.services.accounting_service import AccountingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounting", tags=["accounting"])

_view = require_permission("accounting", "view")
_create = require_permission("accounting", "create")
_post = require_permission("accounting", "post")
_void = require_permission("accounting", "void")


# ---------------------------------------------------------------------------
# Plan de cuentas
# ---------------------------------------------------------------------------

@router.post("/accounts", response_model=ChartOfAccountOut, status_code=201)
def create_account(
    body: ChartOfAccountCreate,
    current_user: User = Depends(_create),
    db: Session = Depends(get_db),
):
    """Crea una nueva cuenta en el plan de cuentas."""
    svc = AccountingService(db)
    return svc.create_account(body)


@router.get("/accounts", response_model=List[ChartOfAccountTree])
def get_accounts_tree(
    company_id: Optional[int] = Query(None),
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """Retorna el plan de cuentas en estructura jerárquica (árbol)."""
    svc = AccountingService(db)
    return svc.get_accounts_tree(company_id)


# ---------------------------------------------------------------------------
# Asientos contables
# ---------------------------------------------------------------------------

@router.post("/entries", response_model=JournalEntryOut, status_code=201)
def create_journal_entry(
    body: JournalEntryCreate,
    current_user: User = Depends(_create),
    db: Session = Depends(get_db),
):
    """
    Crea un asiento contable en estado borrador.
    Valida que SUM(débitos) == SUM(créditos) antes de persistir.
    Retorna HTTP 422 si el asiento no cuadra.
    """
    svc = AccountingService(db)
    entry = svc.create_journal_entry(body, created_by_id=current_user.id)
    return JournalEntryOut.model_validate(entry)


@router.get("/entries", response_model=dict)
def list_journal_entries(
    company_id: Optional[int] = Query(None),
    fiscal_period_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None, description="draft | posted | voided"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """Lista asientos con filtros y paginación."""
    from app.repositories.repositories import JournalEntryRepository
    repo = JournalEntryRepository(db)
    offset = (page - 1) * page_size
    items, total = repo.get_all(
        company_id=company_id,
        fiscal_period_id=fiscal_period_id,
        status=status,
        offset=offset,
        limit=page_size,
    )
    return {
        "items": [JournalEntryOut.model_validate(e) for e in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.post("/entries/{entry_id}/post", response_model=JournalEntryOut)
def post_entry(
    entry_id: int,
    current_user: User = Depends(_post),
    db: Session = Depends(get_db),
):
    """Publica un asiento borrador. No puede revertirse directamente."""
    svc = AccountingService(db)
    entry = svc.post_entry(entry_id, user_id=current_user.id)
    return JournalEntryOut.model_validate(entry)


@router.post("/entries/{entry_id}/void", response_model=JournalEntryOut)
def void_entry(
    entry_id: int,
    reason: str = Query("Anulación manual"),
    current_user: User = Depends(_void),
    db: Session = Depends(get_db),
):
    """Anula un asiento publicado creando un asiento inverso automáticamente."""
    svc = AccountingService(db)
    entry = svc.void_entry(entry_id, user_id=current_user.id, reason=reason)
    return JournalEntryOut.model_validate(entry)


# ---------------------------------------------------------------------------
# Mayor de cuenta y balance de comprobación
# ---------------------------------------------------------------------------

@router.get("/ledger/{account_id}", response_model=dict)
def get_ledger(
    account_id: int,
    fiscal_period_id: Optional[int] = Query(None),
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """Retorna el mayor de una cuenta con saldo acumulado por línea."""
    svc = AccountingService(db)
    account, ledger = svc.get_ledger(account_id, fiscal_period_id)
    return {
        "account_id": account.id,
        "account_code": account.code,
        "account_name": account.name,
        "account_type": account.account_type,
        "lines": [l.model_dump() for l in ledger],
        "final_balance": ledger[-1].balance if ledger else 0.0,
    }


@router.get("/trial-balance", response_model=List[TrialBalanceLine])
def get_trial_balance(
    company_id: Optional[int] = Query(None),
    fiscal_period_id: Optional[int] = Query(None),
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """Balance de comprobación: débitos, créditos y saldo neto por cuenta."""
    svc = AccountingService(db)
    return svc.get_trial_balance(company_id, fiscal_period_id)


# ---------------------------------------------------------------------------
# Períodos Fiscales
# ---------------------------------------------------------------------------

@router.get("/fiscal-periods", response_model=List[FiscalPeriodOut])
def list_fiscal_periods(
    company_id: Optional[int] = Query(None),
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """Lista todos los períodos fiscales."""
    from app.repositories.repositories import FiscalPeriodRepository
    repo = FiscalPeriodRepository(db)
    return repo.get_all(company_id)


@router.post("/fiscal-periods", response_model=FiscalPeriodOut, status_code=201)
def create_fiscal_period(
    body: FiscalPeriodCreate,
    current_user: User = Depends(_create),
    db: Session = Depends(get_db),
):
    """Crea un nuevo período fiscal."""
    from app.repositories.repositories import FiscalPeriodRepository
    repo = FiscalPeriodRepository(db)
    return repo.create(body.model_dump())


@router.post("/fiscal-periods/{period_id}/close", response_model=FiscalPeriodOut)
def close_fiscal_period(
    period_id: int,
    current_user: User = Depends(_void),
    db: Session = Depends(get_db),
):
    """Cierra un período fiscal (solo admins)."""
    from app.repositories.repositories import FiscalPeriodRepository
    repo = FiscalPeriodRepository(db)
    period = repo.close_period(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Período no encontrado")
    return period
