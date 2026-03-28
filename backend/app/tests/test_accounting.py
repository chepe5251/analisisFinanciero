"""
Tests para el módulo de contabilidad general.

Verifica:
- Cuadre de asientos (SUM débitos == SUM créditos)
- Error HTTP 422 en asiento desbalanceado
- Publicación y anulación correcta de asientos
- Balance de comprobación
"""
import pytest
from datetime import datetime

from app.services.accounting_service import AccountingService
from app.schemas.schemas import JournalEntryCreate, JournalEntryLineCreate, ChartOfAccountCreate


def make_entry(fiscal_period_id: int, account_id_1: int, account_id_2: int,
               debit: float, credit: float, description: str = "Test entry") -> JournalEntryCreate:
    return JournalEntryCreate(
        fiscal_period_id=fiscal_period_id,
        entry_date=datetime(2024, 1, 15),
        description=description,
        lines=[
            JournalEntryLineCreate(account_id=account_id_1, debit=debit, credit=0.0),
            JournalEntryLineCreate(account_id=account_id_2, debit=0.0, credit=credit),
        ],
    )


class TestJournalEntryBalance:
    def test_balanced_entry_is_created(self, db, fiscal_period, income_account, expense_account):
        """Un asiento donde débitos == créditos debe persistirse correctamente."""
        svc = AccountingService(db)
        data = make_entry(fiscal_period.id, expense_account.id, income_account.id, 1000.0, 1000.0)
        entry = svc.create_journal_entry(data)
        assert entry.id is not None
        assert entry.status == "draft"
        assert len(entry.lines) == 2

    def test_unbalanced_entry_raises_422(self, db, fiscal_period, income_account, expense_account):
        """Un asiento con débitos != créditos debe fallar con HTTP 422."""
        from fastapi import HTTPException
        svc = AccountingService(db)
        data = make_entry(fiscal_period.id, expense_account.id, income_account.id, 1000.0, 900.0)
        with pytest.raises(HTTPException) as exc_info:
            svc.create_journal_entry(data)
        assert exc_info.value.status_code == 422
        assert "no cuadra" in exc_info.value.detail.lower()

    def test_zero_entry_raises_422(self, db, fiscal_period, income_account, expense_account):
        """Un asiento con todas las líneas en cero debe fallar."""
        from fastapi import HTTPException
        svc = AccountingService(db)
        data = make_entry(fiscal_period.id, expense_account.id, income_account.id, 0.0, 0.0)
        with pytest.raises(HTTPException) as exc_info:
            svc.create_journal_entry(data)
        assert exc_info.value.status_code == 422

    def test_closed_period_raises_422(self, db, fiscal_period, income_account, expense_account):
        """No se puede crear un asiento en un período cerrado."""
        from fastapi import HTTPException
        fiscal_period.status = "closed"
        db.commit()
        svc = AccountingService(db)
        data = make_entry(fiscal_period.id, expense_account.id, income_account.id, 500.0, 500.0)
        with pytest.raises(HTTPException) as exc_info:
            svc.create_journal_entry(data)
        assert exc_info.value.status_code == 422
        # Restaurar para otros tests
        fiscal_period.status = "open"
        db.commit()


class TestPostEntry:
    def test_post_draft_entry(self, db, fiscal_period, income_account, expense_account):
        """Publicar un asiento draft lo cambia a posted."""
        svc = AccountingService(db)
        data = make_entry(fiscal_period.id, expense_account.id, income_account.id, 500.0, 500.0)
        entry = svc.create_journal_entry(data)
        posted = svc.post_entry(entry.id)
        assert posted.status == "posted"

    def test_post_already_posted_raises_422(self, db, fiscal_period, income_account, expense_account):
        """Publicar un asiento ya publicado debe fallar."""
        from fastapi import HTTPException
        svc = AccountingService(db)
        data = make_entry(fiscal_period.id, expense_account.id, income_account.id, 200.0, 200.0)
        entry = svc.create_journal_entry(data)
        svc.post_entry(entry.id)
        with pytest.raises(HTTPException) as exc_info:
            svc.post_entry(entry.id)
        assert exc_info.value.status_code == 422


class TestVoidEntry:
    def test_void_posted_entry(self, db, fiscal_period, income_account, expense_account):
        """Anular un asiento publicado crea asiento inverso y marca el original como voided."""
        svc = AccountingService(db)
        data = make_entry(fiscal_period.id, expense_account.id, income_account.id, 300.0, 300.0)
        entry = svc.create_journal_entry(data)
        svc.post_entry(entry.id)
        voided = svc.void_entry(entry.id, reason="Error de captura")
        assert voided.status == "voided"
        assert voided.void_reason == "Error de captura"

    def test_void_draft_raises_422(self, db, fiscal_period, income_account, expense_account):
        """No se puede anular un asiento en borrador."""
        from fastapi import HTTPException
        svc = AccountingService(db)
        data = make_entry(fiscal_period.id, expense_account.id, income_account.id, 100.0, 100.0)
        entry = svc.create_journal_entry(data)
        with pytest.raises(HTTPException) as exc_info:
            svc.void_entry(entry.id)
        assert exc_info.value.status_code == 422


class TestTrialBalance:
    def test_trial_balance_returns_accounts(self, db, fiscal_period, income_account, expense_account):
        """El balance de comprobación debe incluir las cuentas con movimientos."""
        svc = AccountingService(db)
        data = make_entry(fiscal_period.id, expense_account.id, income_account.id, 700.0, 700.0)
        entry = svc.create_journal_entry(data)
        svc.post_entry(entry.id)
        trial = svc.get_trial_balance(fiscal_period_id=fiscal_period.id)
        codes = [t.account_code for t in trial]
        assert "4001" in codes  # income
        assert "5001" in codes  # expense

    def test_trial_balance_debits_equal_credits(self, db, fiscal_period, income_account, expense_account):
        """En el balance de comprobación, la suma de débitos debe igualar la de créditos."""
        svc = AccountingService(db)
        data = make_entry(fiscal_period.id, expense_account.id, income_account.id, 400.0, 400.0)
        entry = svc.create_journal_entry(data)
        svc.post_entry(entry.id)
        trial = svc.get_trial_balance(fiscal_period_id=fiscal_period.id)
        total_debit = sum(t.total_debit for t in trial)
        total_credit = sum(t.total_credit for t in trial)
        assert abs(total_debit - total_credit) < 0.01
