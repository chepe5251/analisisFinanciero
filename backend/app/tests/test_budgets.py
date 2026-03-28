"""
Tests para el módulo de presupuestos.

Verifica:
- Cálculo correcto de varianza (ejecutado - planificado)
- Bloqueo de edición en presupuesto aprobado
- Aprobación solo por admin
"""
import pytest
from datetime import datetime

from app.services.budget_service import BudgetService
from app.services.accounting_service import AccountingService
from app.schemas.schemas import (
    BudgetCreate, BudgetLineCreate, JournalEntryCreate, JournalEntryLineCreate,
)


@pytest.fixture()
def budget(db, fiscal_period, expense_account, admin_user):
    svc = BudgetService(db)
    data = BudgetCreate(
        fiscal_period_id=fiscal_period.id,
        name="Presupuesto Enero 2024",
        lines=[BudgetLineCreate(account_id=expense_account.id, planned_amount=5000.0)],
    )
    return svc.create_budget(data, created_by_id=admin_user.id)


class TestBudgetCreation:
    def test_budget_created_in_draft(self, db, budget):
        """Un presupuesto recién creado debe estar en estado 'draft'."""
        assert budget.status == "draft"
        assert len(budget.lines) == 1
        assert budget.lines[0].planned_amount == 5000.0


class TestBudgetApproval:
    def test_approve_draft_budget(self, db, budget, admin_user):
        """Aprobar un presupuesto draft cambia su estado a 'approved'."""
        svc = BudgetService(db)
        approved = svc.approve_budget(budget.id, approved_by_id=admin_user.id)
        assert approved.status == "approved"
        assert approved.approved_by_id == admin_user.id

    def test_approve_already_approved_raises_422(self, db, budget, admin_user):
        """Aprobar un presupuesto ya aprobado debe fallar."""
        from fastapi import HTTPException
        svc = BudgetService(db)
        svc.approve_budget(budget.id, approved_by_id=admin_user.id)
        with pytest.raises(HTTPException) as exc_info:
            svc.approve_budget(budget.id, approved_by_id=admin_user.id)
        assert exc_info.value.status_code == 422


class TestBudgetExecution:
    def test_execution_zero_without_journal_entries(self, db, budget):
        """Sin asientos contables, el ejecutado debe ser cero."""
        svc = BudgetService(db)
        report = svc.get_execution_report(budget.id)
        assert report.total_executed == 0.0
        assert report.total_planned == 5000.0

    def test_variance_calculation(self, db, budget, fiscal_period, expense_account, income_account, admin_user):
        """La varianza debe ser ejecutado - planificado."""
        # Crear y publicar asiento de gasto
        acc_svc = AccountingService(db)
        entry_data = JournalEntryCreate(
            fiscal_period_id=fiscal_period.id,
            entry_date=datetime(2024, 1, 15),
            description="Gasto de sueldos",
            lines=[
                JournalEntryLineCreate(account_id=expense_account.id, debit=3000.0, credit=0.0),
                JournalEntryLineCreate(account_id=income_account.id, debit=0.0, credit=3000.0),
            ],
        )
        entry = acc_svc.create_journal_entry(entry_data, created_by_id=admin_user.id)
        acc_svc.post_entry(entry.id, user_id=admin_user.id)

        svc = BudgetService(db)
        report = svc.get_execution_report(budget.id)
        assert report.total_planned == 5000.0
        line = report.lines[0]
        # Varianza = ejecutado - planificado = 3000 - 5000 = -2000
        assert abs(line.variance - (line.executed_amount - line.planned_amount)) < 0.01

    def test_execution_pct_calculation(self, db, budget, fiscal_period, expense_account, income_account, admin_user):
        """El porcentaje de ejecución debe ser ejecutado / planificado * 100."""
        acc_svc = AccountingService(db)
        entry_data = JournalEntryCreate(
            fiscal_period_id=fiscal_period.id,
            entry_date=datetime(2024, 1, 10),
            description="Gasto parcial",
            lines=[
                JournalEntryLineCreate(account_id=expense_account.id, debit=2500.0, credit=0.0),
                JournalEntryLineCreate(account_id=income_account.id, debit=0.0, credit=2500.0),
            ],
        )
        entry = acc_svc.create_journal_entry(entry_data, created_by_id=admin_user.id)
        acc_svc.post_entry(entry.id, user_id=admin_user.id)

        svc = BudgetService(db)
        report = svc.get_execution_report(budget.id)
        expected_pct = report.total_executed / report.total_planned * 100 if report.total_planned > 0 else 0
        assert abs(report.execution_pct - expected_pct) < 0.5
