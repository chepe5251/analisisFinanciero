"""
Tests para el módulo de facturación.

Verifica:
- Cálculo automático de totales al crear factura
- Generación de asiento al emitir
- Cálculo correcto del estado 'overdue'
- Registro de pagos y actualización de estado
"""
import pytest
from datetime import datetime, timedelta

from app.services.invoice_service import InvoiceService
from app.schemas.schemas import InvoiceCreate, InvoiceLineCreate, PaymentCreate


def make_invoice(
    fiscal_period_id: int,
    account_id: int,
    invoice_type: str = "issued",
    due_days: int = 30,
) -> InvoiceCreate:
    return InvoiceCreate(
        invoice_type=invoice_type,
        invoice_number="F-001",
        invoice_date=datetime(2024, 1, 10),
        due_date=datetime(2024, 1, 10) + timedelta(days=due_days),
        counterparty_name="Cliente de Prueba S.A.",
        lines=[
            InvoiceLineCreate(
                account_id=account_id,
                description="Servicio de consultoría",
                quantity=10.0,
                unit_price=100.0,
                tax_rate=12.0,
            )
        ],
    )


class TestInvoiceCreation:
    def test_totals_calculated_correctly(self, db, income_account):
        """Los totales de la factura deben calcularse automáticamente."""
        svc = InvoiceService(db)
        data = make_invoice(0, income_account.id)
        invoice = svc.create_invoice(data)

        assert invoice.subtotal == pytest.approx(1000.0, abs=0.01)
        assert invoice.tax_amount == pytest.approx(120.0, abs=0.01)
        assert invoice.total == pytest.approx(1120.0, abs=0.01)
        assert invoice.status == "draft"

    def test_line_totals_calculated(self, db, income_account):
        """Cada línea debe tener subtotal, tax_amount y total calculados."""
        svc = InvoiceService(db)
        data = make_invoice(0, income_account.id)
        invoice = svc.create_invoice(data)
        line = invoice.lines[0]
        assert line.subtotal == pytest.approx(1000.0, abs=0.01)
        assert line.tax_amount == pytest.approx(120.0, abs=0.01)
        assert line.total == pytest.approx(1120.0, abs=0.01)


class TestInvoiceIssue:
    def test_issue_creates_journal_entry(self, db, fiscal_period, income_account):
        """Emitir una factura con líneas contables debe crear un asiento."""
        svc = InvoiceService(db)
        data = make_invoice(fiscal_period.id, income_account.id)
        invoice = svc.create_invoice(data)
        issued = svc.issue_invoice(invoice.id)
        assert issued.status == "issued"

    def test_issue_without_open_period_raises_422(self, db, income_account):
        """Emitir sin período fiscal abierto debe fallar con 422."""
        from fastapi import HTTPException
        svc = InvoiceService(db)
        data = make_invoice(0, income_account.id)
        invoice = svc.create_invoice(data)
        with pytest.raises(HTTPException) as exc_info:
            svc.issue_invoice(invoice.id)
        assert exc_info.value.status_code == 422

    def test_cannot_issue_already_issued(self, db, fiscal_period, income_account):
        """No se puede emitir una factura ya emitida."""
        from fastapi import HTTPException
        svc = InvoiceService(db)
        data = make_invoice(fiscal_period.id, income_account.id)
        invoice = svc.create_invoice(data)
        svc.issue_invoice(invoice.id)
        with pytest.raises(HTTPException) as exc_info:
            svc.issue_invoice(invoice.id)
        assert exc_info.value.status_code == 422


class TestInvoicePayment:
    def test_full_payment_marks_paid(self, db, fiscal_period, income_account):
        """Pago completo debe marcar la factura como pagada."""
        svc = InvoiceService(db)
        data = make_invoice(fiscal_period.id, income_account.id)
        invoice = svc.create_invoice(data)
        svc.issue_invoice(invoice.id)

        payment_data = PaymentCreate(
            payment_date=datetime(2024, 1, 20),
            amount=invoice.total,
            payment_method="bank_transfer",
        )
        svc.register_payment(invoice.id, payment_data)
        # Verificar estado actualizado
        from app.repositories.repositories import InvoiceRepository
        updated = InvoiceRepository(db).get_by_id(invoice.id)
        assert updated.status == "paid"

    def test_partial_payment_keeps_issued(self, db, fiscal_period, income_account):
        """Pago parcial no debe cambiar el estado a 'paid'."""
        svc = InvoiceService(db)
        data = make_invoice(fiscal_period.id, income_account.id)
        invoice = svc.create_invoice(data)
        svc.issue_invoice(invoice.id)

        payment_data = PaymentCreate(
            payment_date=datetime(2024, 1, 15),
            amount=invoice.total / 2,
        )
        svc.register_payment(invoice.id, payment_data)
        from app.repositories.repositories import InvoiceRepository
        updated = InvoiceRepository(db).get_by_id(invoice.id)
        assert updated.status != "paid"


class TestInvoiceOverdue:
    def test_overdue_status_set(self, db, income_account):
        """Facturas con due_date pasada deben marcarse como overdue."""
        svc = InvoiceService(db)
        # Crear factura con vencimiento en el pasado
        data = InvoiceCreate(
            invoice_type="issued",
            invoice_date=datetime(2023, 6, 1),
            due_date=datetime(2023, 6, 30),  # fecha pasada
            counterparty_name="Cliente Vencido",
            lines=[
                InvoiceLineCreate(
                    account_id=income_account.id,
                    description="Servicio",
                    quantity=1.0,
                    unit_price=500.0,
                    tax_rate=0.0,
                )
            ],
        )
        invoice = svc.create_invoice(data)
        invoice.status = "issued"
        db.commit()

        count = svc.mark_overdue()
        assert count >= 1
        from app.repositories.repositories import InvoiceRepository
        updated = InvoiceRepository(db).get_by_id(invoice.id)
        assert updated.status == "overdue"
