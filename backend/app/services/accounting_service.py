"""
Servicio de contabilidad general.

Reglas de negocio:
  - Cada asiento debe cuadrar: SUM(débitos) == SUM(créditos). Validar antes de persistir.
  - No se puede editar ni eliminar un asiento publicado; solo anular (asiento inverso).
  - Los períodos cerrados no aceptan nuevos asientos.
  - La conciliación bancaria puede generar asientos automáticos.
"""
import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.models import (
    JournalEntry, JournalEntryLine, ChartOfAccount, FiscalPeriod,
)
from app.schemas.schemas import (
    JournalEntryCreate, JournalEntryOut, LedgerLine, TrialBalanceLine,
    ChartOfAccountCreate, ChartOfAccountOut, ChartOfAccountTree,
)
from app.repositories.repositories import (
    JournalEntryRepository, ChartOfAccountRepository,
    FiscalPeriodRepository,
)

logger = logging.getLogger(__name__)

BALANCE_TOLERANCE = 0.01


class AccountingService:
    def __init__(self, db: Session):
        self.db = db
        self.entry_repo = JournalEntryRepository(db)
        self.account_repo = ChartOfAccountRepository(db)
        self.period_repo = FiscalPeriodRepository(db)

    # ------------------------------------------------------------------
    # Plan de cuentas
    # ------------------------------------------------------------------

    def create_account(self, data: ChartOfAccountCreate) -> ChartOfAccount:
        existing = self.account_repo.get_by_code(data.code, data.company_id)
        if existing:
            raise HTTPException(status_code=409, detail=f"Ya existe una cuenta con código '{data.code}'.")
        if data.parent_id:
            parent = self.account_repo.get_by_id(data.parent_id)
            if not parent:
                raise HTTPException(status_code=404, detail=f"Cuenta padre {data.parent_id} no encontrada.")
        account_data = data.model_dump()
        return self.account_repo.create(account_data)

    def get_accounts_tree(self, company_id: Optional[int] = None) -> List[ChartOfAccountTree]:
        """Construye el árbol de cuentas a partir de las raíces."""
        all_accounts = self.account_repo.get_all(company_id)
        by_id: Dict[int, ChartOfAccountTree] = {}
        for acc in all_accounts:
            by_id[acc.id] = ChartOfAccountTree.model_validate(acc)

        roots: List[ChartOfAccountTree] = []
        for acc in all_accounts:
            node = by_id[acc.id]
            if acc.parent_id and acc.parent_id in by_id:
                by_id[acc.parent_id].children.append(node)
            else:
                roots.append(node)
        return roots

    # ------------------------------------------------------------------
    # Asientos contables
    # ------------------------------------------------------------------

    def create_journal_entry(
        self,
        data: JournalEntryCreate,
        created_by_id: Optional[int] = None,
    ) -> JournalEntry:
        # Validar que el período está abierto
        period = self.period_repo.get_by_id(data.fiscal_period_id)
        if not period:
            raise HTTPException(status_code=404, detail="Período fiscal no encontrado.")
        if period.status == "closed":
            raise HTTPException(
                status_code=422,
                detail=f"El período '{period.name}' está cerrado. No se aceptan nuevos asientos.",
            )

        # Validar cuadre: SUM(débitos) == SUM(créditos)
        total_debit = sum(line.debit for line in data.lines)
        total_credit = sum(line.credit for line in data.lines)
        if abs(total_debit - total_credit) > BALANCE_TOLERANCE:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"El asiento no cuadra: débitos={total_debit:.2f}, créditos={total_credit:.2f}. "
                    f"Diferencia={abs(total_debit - total_credit):.2f}. "
                    "SUM(débitos) debe ser igual a SUM(créditos)."
                ),
            )
        if total_debit == 0:
            raise HTTPException(status_code=422, detail="El asiento no puede tener todas las líneas en cero.")

        # Validar que las cuentas existen
        for line in data.lines:
            account = self.account_repo.get_by_id(line.account_id)
            if not account:
                raise HTTPException(status_code=404, detail=f"Cuenta {line.account_id} no encontrada.")

        entry_data = {
            "company_id": data.company_id,
            "fiscal_period_id": data.fiscal_period_id,
            "cost_center_id": data.cost_center_id,
            "entry_date": data.entry_date,
            "description": data.description,
            "reference": data.reference,
            "status": "draft",
            "created_by_id": created_by_id,
        }
        lines_data = [
            {
                "account_id": line.account_id,
                "description": line.description,
                "debit": line.debit,
                "credit": line.credit,
            }
            for line in data.lines
        ]
        return self.entry_repo.create(entry_data, lines_data)

    def post_entry(self, entry_id: int, user_id: Optional[int] = None) -> JournalEntry:
        """Publica un asiento borrador. No puede publicarse un asiento ya publicado o anulado."""
        entry = self.entry_repo.get_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Asiento no encontrado.")
        if entry.status != "draft":
            raise HTTPException(
                status_code=422,
                detail=f"Solo se pueden publicar asientos en estado 'draft'. Estado actual: '{entry.status}'.",
            )
        period = self.period_repo.get_by_id(entry.fiscal_period_id)
        if period and period.status == "closed":
            raise HTTPException(
                status_code=422,
                detail=f"El período '{period.name}' está cerrado.",
            )
        entry.status = "posted"
        self.db.commit()
        self.db.refresh(entry)
        logger.info("Asiento publicado: entry_id=%d user_id=%s", entry_id, user_id)
        return entry

    def void_entry(
        self, entry_id: int, user_id: Optional[int] = None, reason: str = "Anulación manual"
    ) -> JournalEntry:
        """
        Anula un asiento publicado creando un asiento inverso.
        El asiento original queda con status='voided'.
        """
        entry = self.entry_repo.get_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Asiento no encontrado.")
        if entry.status != "posted":
            raise HTTPException(
                status_code=422,
                detail=f"Solo se pueden anular asientos publicados. Estado actual: '{entry.status}'.",
            )
        period = self.period_repo.get_by_id(entry.fiscal_period_id)
        if period and period.status == "closed":
            raise HTTPException(
                status_code=422,
                detail=f"El período '{period.name}' está cerrado. No se puede anular.",
            )

        # Crear asiento inverso
        reverse_lines_data = [
            {
                "account_id": line.account_id,
                "description": f"Anulación: {line.description or ''}",
                "debit": line.credit,
                "credit": line.debit,
            }
            for line in entry.lines
        ]
        reverse_entry_data = {
            "company_id": entry.company_id,
            "fiscal_period_id": entry.fiscal_period_id,
            "cost_center_id": entry.cost_center_id,
            "entry_date": datetime.utcnow(),
            "description": f"ANULACIÓN DE: {entry.description}",
            "reference": f"VOID-{entry.id}",
            "status": "posted",
            "created_by_id": user_id,
            "source_type": "void",
            "source_id": entry.id,
        }
        self.entry_repo.create(reverse_entry_data, reverse_lines_data)

        # Marcar original como anulado
        entry.status = "voided"
        entry.voided_by_id = user_id
        entry.void_reason = reason
        self.db.commit()
        self.db.refresh(entry)
        logger.info("Asiento anulado: entry_id=%d user_id=%s", entry_id, user_id)
        return entry

    # ------------------------------------------------------------------
    # Mayor de cuenta
    # ------------------------------------------------------------------

    def get_ledger(
        self,
        account_id: int,
        fiscal_period_id: Optional[int] = None,
    ) -> Tuple[ChartOfAccount, List[LedgerLine]]:
        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

        lines = self.entry_repo.get_lines_for_account(account_id, fiscal_period_id)
        ledger: List[LedgerLine] = []
        balance = 0.0
        for line in lines:
            balance += line.debit - line.credit
            ledger.append(LedgerLine(
                entry_id=line.entry_id,
                entry_date=line.entry.entry_date,
                description=line.entry.description,
                reference=line.entry.reference,
                debit=line.debit,
                credit=line.credit,
                balance=balance,
            ))
        return account, ledger

    # ------------------------------------------------------------------
    # Balance de comprobación
    # ------------------------------------------------------------------

    def get_trial_balance(
        self,
        company_id: Optional[int] = None,
        fiscal_period_id: Optional[int] = None,
    ) -> List[TrialBalanceLine]:
        rows = self.entry_repo.get_trial_balance(company_id, fiscal_period_id)
        return [TrialBalanceLine(**row) for row in rows]
