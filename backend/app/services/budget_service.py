"""
Servicio de presupuestos.

Reglas de negocio:
  - Un presupuesto aprobado no puede modificarse; solo crear una revisión.
  - El monto ejecutado se calcula en tiempo real desde journal_entry_lines.
  - Varianza = ejecutado - planificado.
"""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.models import Budget, BudgetLine, ChartOfAccount, FiscalPeriod
from app.schemas.schemas import (
    BudgetCreate, BudgetOut,
    BudgetExecutionReport, BudgetExecutionLine,
)
from app.repositories.repositories import (
    BudgetRepository, ChartOfAccountRepository, FiscalPeriodRepository,
)

logger = logging.getLogger(__name__)


class BudgetService:
    def __init__(self, db: Session):
        self.db = db
        self.budget_repo = BudgetRepository(db)
        self.account_repo = ChartOfAccountRepository(db)
        self.period_repo = FiscalPeriodRepository(db)

    def create_budget(self, data: BudgetCreate, created_by_id: Optional[int] = None) -> Budget:
        period = self.period_repo.get_by_id(data.fiscal_period_id)
        if not period:
            raise HTTPException(status_code=404, detail="Período fiscal no encontrado.")

        budget_data = {
            "company_id": data.company_id,
            "fiscal_period_id": data.fiscal_period_id,
            "cost_center_id": data.cost_center_id,
            "name": data.name,
            "status": "draft",
            "created_by_id": created_by_id,
        }
        lines_data = [
            {"account_id": line.account_id, "planned_amount": line.planned_amount}
            for line in data.lines
        ]
        return self.budget_repo.create(budget_data, lines_data)

    def get_budgets(self, company_id: Optional[int] = None) -> List[Budget]:
        return self.budget_repo.get_all(company_id)

    def get_budget(self, budget_id: int) -> Budget:
        budget = self.budget_repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")
        return budget

    def approve_budget(self, budget_id: int, approved_by_id: int) -> Budget:
        budget = self.budget_repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")
        if budget.status != "draft":
            raise HTTPException(
                status_code=422,
                detail=f"Solo se puede aprobar un presupuesto en estado 'draft'. Estado actual: '{budget.status}'.",
            )
        return self.budget_repo.approve(budget_id, approved_by_id)

    def get_execution_report(self, budget_id: int) -> BudgetExecutionReport:
        budget = self.budget_repo.get_by_id(budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")

        period = self.period_repo.get_by_id(budget.fiscal_period_id)
        period_name = period.name if period else str(budget.fiscal_period_id)

        lines_out: List[BudgetExecutionLine] = []
        total_planned = 0.0
        total_executed = 0.0

        for line in budget.lines:
            account = self.account_repo.get_by_id(line.account_id)
            executed = self.budget_repo.get_executed_amount(budget_id, line.account_id)
            planned = line.planned_amount
            variance = executed - planned
            pct = (executed / planned * 100) if planned != 0 else 0.0

            lines_out.append(BudgetExecutionLine(
                account_id=line.account_id,
                account_code=account.code if account else "",
                account_name=account.name if account else "",
                planned_amount=planned,
                executed_amount=executed,
                variance=variance,
                execution_pct=round(pct, 2),
            ))
            total_planned += planned
            total_executed += executed

        total_variance = total_executed - total_planned
        total_pct = (total_executed / total_planned * 100) if total_planned != 0 else 0.0

        return BudgetExecutionReport(
            budget_id=budget.id,
            budget_name=budget.name,
            fiscal_period=period_name,
            status=budget.status,
            total_planned=total_planned,
            total_executed=total_executed,
            total_variance=total_variance,
            execution_pct=round(total_pct, 2),
            lines=lines_out,
        )
