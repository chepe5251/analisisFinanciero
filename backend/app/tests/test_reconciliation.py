"""
Tests de la lógica de conciliación.
Usa objetos en memoria (sin base de datos real) para probar el algoritmo.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.services.reconciliation_service import ReconciliationService
from app.models.models import EmployeeTemplate, BankTransaction
from app.schemas.schemas import ReconciliationRunRequest


def make_template(
    id, employee_id, full_name, bank_name, account_number, expected_amount
) -> EmployeeTemplate:
    t = EmployeeTemplate()
    t.id = id
    t.employee_id = employee_id
    t.full_name = full_name
    t.bank_name = bank_name
    t.account_number = account_number
    t.expected_amount = expected_amount
    t.currency = "USD"
    return t


def make_transaction(
    id, upload_id, bank_name, beneficiary_name, account, amount, reference=None
) -> BankTransaction:
    tx = BankTransaction()
    tx.id = id
    tx.upload_id = upload_id
    tx.bank_name = bank_name
    tx.beneficiary_name = beneficiary_name
    tx.beneficiary_account = account
    tx.amount = amount
    tx.reference = reference
    tx.currency = "USD"
    tx.transaction_date = datetime(2024, 1, 15)
    return tx


class TestReconciliationAlgorithm:
    """Prueba _perform_reconciliation directamente con datos sintéticos."""

    def setup_method(self):
        self.db = MagicMock()
        self.service = ReconciliationService(self.db)

    def test_exact_match_by_account(self):
        """Un empleado con transacción exacta debe quedar 'matched'."""
        templates = [make_template(1, "EMP001", "Juan Pérez", "Banco_A", "1234567890", 1500.0)]
        transactions = [make_transaction(1, 1, "Banco_A", "Juan Pérez", "1234567890", 1500.0)]

        results = self.service._perform_reconciliation(templates, transactions)

        assert len(results) == 1
        assert results[0].reconciliation_status == "matched"
        assert results[0].matched_by == "account"
        assert results[0].difference_amount == 0.0

    def test_difference_by_account(self):
        """Misma cuenta pero monto distinto → 'difference'."""
        templates = [make_template(1, "EMP001", "Juan Pérez", "Banco_A", "1234567890", 1500.0)]
        transactions = [make_transaction(1, 1, "Banco_A", "Juan Pérez", "1234567890", 1250.0)]

        results = self.service._perform_reconciliation(templates, transactions)

        assert results[0].reconciliation_status == "difference"
        assert results[0].difference_amount == pytest.approx(-250.0)

    def test_missing_employee(self):
        """Empleado en plantilla sin transacción → 'missing'."""
        templates = [make_template(1, "EMP001", "Juan Pérez", "Banco_A", "1234567890", 1500.0)]
        transactions = []

        results = self.service._perform_reconciliation(templates, transactions)

        assert len(results) == 1
        assert results[0].reconciliation_status == "missing"
        assert results[0].bank_transaction_id is None

    def test_extra_transaction(self):
        """Transacción sin empleado en plantilla → 'extra'."""
        templates = []
        transactions = [make_transaction(1, 1, "Banco_A", "Desconocido", "9999999999", 500.0)]

        results = self.service._perform_reconciliation(templates, transactions)

        assert len(results) == 1
        assert results[0].reconciliation_status == "extra"
        assert results[0].employee_template_id is None

    def test_name_similarity_match(self):
        """Nombre con acento vs sin acento en mismo banco → match por similitud."""
        templates = [make_template(1, "EMP010", "Carmen Jiménez", "Banco_C", "2233445566", 1050.0)]
        # La transacción tiene el nombre sin tilde
        transactions = [make_transaction(1, 1, "Banco_C", "Carmen Jimenez", "2233445566", 1050.0)]

        results = self.service._perform_reconciliation(templates, transactions)

        # Debe matchear por cuenta (mismo número de cuenta)
        assert results[0].reconciliation_status == "matched"

    def test_name_similarity_without_account(self):
        """Match por nombre cuando no hay número de cuenta."""
        templates = [make_template(1, "EMP010", "Carmen Jiménez", "Banco_C", "2233445566", 1050.0)]
        tx = make_transaction(1, 1, "Banco_C", "Carmen Jimenez", None, 1050.0)

        results = self.service._perform_reconciliation([templates[0]], [tx])

        assert results[0].reconciliation_status in ("matched", "difference")
        assert results[0].matched_by in ("name_similarity", "account")

    def test_match_by_employee_id_in_reference(self):
        """employee_id en campo reference → debe matchear aunque no haya cuenta."""
        templates = [make_template(1, "EMP001", "Juan Pérez", "Banco_A", "1234567890", 1500.0)]
        tx = make_transaction(1, 1, "Banco_A", "J. Pérez", None, 1500.0, reference="Pago EMP001 enero")

        results = self.service._perform_reconciliation([templates[0]], [tx])

        assert results[0].reconciliation_status == "matched"
        assert results[0].matched_by == "employee_id_in_reference"

    def test_duplicate_detection(self):
        """Dos transacciones para la misma cuenta en el mismo upload → duplicate."""
        templates = [make_template(1, "EMP006", "Laura Sánchez", "Banco_B", "3344556677", 1350.0)]
        tx1 = make_transaction(1, 1, "Banco_B", "Laura Sanchez", "3344556677", 1350.0)
        tx2 = make_transaction(2, 1, "Banco_B", "Laura Sanchez", "3344556677", 1350.0)

        results = self.service._perform_reconciliation([templates[0]], [tx1, tx2])

        statuses = {r.reconciliation_status for r in results}
        assert "duplicate" in statuses

    def test_amount_tolerance(self):
        """Diferencia menor a AMOUNT_TOLERANCE se considera matched."""
        templates = [make_template(1, "EMP001", "Juan", "Banco_A", "111", 1500.0)]
        transactions = [make_transaction(1, 1, "Banco_A", "Juan", "111", 1500.005)]

        results = self.service._perform_reconciliation(templates, transactions)
        assert results[0].reconciliation_status == "matched"

    def test_multiple_employees_multiple_banks(self):
        """Escenario completo con 3 empleados de 2 bancos."""
        templates = [
            make_template(1, "EMP001", "Juan Pérez", "Banco_A", "1111", 1500.0),
            make_template(2, "EMP002", "María García", "Banco_A", "2222", 1200.0),
            make_template(3, "EMP003", "Carlos López", "Banco_B", "3333", 1800.0),
        ]
        transactions = [
            make_transaction(1, 1, "Banco_A", "Juan Pérez", "1111", 1500.0),
            make_transaction(2, 1, "Banco_A", "María García", "2222", 1100.0),  # diferencia
            # Carlos no tiene transacción → missing
        ]

        results = self.service._perform_reconciliation(templates, transactions)

        by_status = {r.reconciliation_status for r in results}
        assert "matched" in by_status
        assert "difference" in by_status
        assert "missing" in by_status
        assert len(results) == 3

    def test_different_bank_no_match(self):
        """Misma cuenta pero banco diferente → NO debe matchear."""
        templates = [make_template(1, "EMP001", "Juan", "Banco_A", "1111", 1500.0)]
        transactions = [make_transaction(1, 1, "Banco_B", "Juan", "1111", 1500.0)]

        results = self.service._perform_reconciliation(templates, transactions)

        statuses = [r.reconciliation_status for r in results]
        # Juan queda missing (banco A no lo encontró) y la transacción queda extra (banco B)
        assert "missing" in statuses
        assert "extra" in statuses
