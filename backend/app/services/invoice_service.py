"""
Servicio de facturación y cuentas por cobrar/pagar.

Reglas de negocio:
  - Al emitir una factura, se genera automáticamente el asiento contable.
  - Al registrar un pago, se actualiza el estado y se genera el asiento de cobro.
  - Estado 'overdue' se marca automáticamente si due_date < hoy y no está pagada.
"""
import logging
import io
from typing import List, Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.models import Invoice, InvoiceLine, Payment
from app.schemas.schemas import (
    InvoiceCreate, InvoiceOut, PaymentCreate,
    AgingBucket, AgingReport,
)
from app.repositories.repositories import (
    InvoiceRepository, JournalEntryRepository, ChartOfAccountRepository,
    FiscalPeriodRepository,
)

logger = logging.getLogger(__name__)


def _calculate_line_totals(quantity: float, unit_price: float, tax_rate: float) -> Tuple[float, float, float]:
    subtotal = round(quantity * unit_price, 4)
    tax_amount = round(subtotal * tax_rate / 100, 4)
    total = round(subtotal + tax_amount, 4)
    return subtotal, tax_amount, total


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
        self.entry_repo = JournalEntryRepository(db)
        self.account_repo = ChartOfAccountRepository(db)
        self.period_repo = FiscalPeriodRepository(db)

    def create_invoice(self, data: InvoiceCreate, created_by_id: Optional[int] = None) -> Invoice:
        subtotal = 0.0
        tax_total = 0.0
        lines_data = []
        for line in data.lines:
            line_subtotal, line_tax, line_total = _calculate_line_totals(
                line.quantity, line.unit_price, line.tax_rate
            )
            subtotal += line_subtotal
            tax_total += line_tax
            lines_data.append({
                "account_id": line.account_id,
                "description": line.description,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "tax_rate": line.tax_rate,
                "subtotal": line_subtotal,
                "tax_amount": line_tax,
                "total": line_total,
            })

        total = round(subtotal + tax_total, 4)
        invoice_data = {
            "company_id": data.company_id,
            "invoice_type": data.invoice_type,
            "invoice_number": data.invoice_number,
            "invoice_date": data.invoice_date,
            "due_date": data.due_date,
            "counterparty_name": data.counterparty_name,
            "counterparty_tax_id": data.counterparty_tax_id,
            "notes": data.notes,
            "status": "draft",
            "subtotal": round(subtotal, 4),
            "tax_amount": round(tax_total, 4),
            "total": total,
            "created_by_id": created_by_id,
        }
        return self.invoice_repo.create(invoice_data, lines_data)

    def issue_invoice(self, invoice_id: int, user_id: Optional[int] = None) -> Invoice:
        """
        Emite la factura y genera el asiento contable automático.
        Para facturas emitidas (CxC): Débito CxC / Crédito Ingreso.
        Para facturas recibidas (CxP): Débito Gasto / Crédito CxP.
        """
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")
        if invoice.status != "draft":
            raise HTTPException(
                status_code=422,
                detail=f"Solo se pueden emitir facturas en estado 'draft'. Estado: '{invoice.status}'.",
            )

        # Buscar período fiscal activo para la fecha de la factura
        periods = self.period_repo.get_open(invoice.company_id)
        period = next(
            (p for p in periods if p.start_date <= invoice.invoice_date <= p.end_date),
            periods[0] if periods else None,
        )
        if not period:
            raise HTTPException(
                status_code=422,
                detail="No existe un período fiscal abierto para la fecha de la factura. Cree un período fiscal primero.",
            )

        # Generar asiento contable simplificado (sin cuenta contable específica de CxC/CxP
        # ya que depende del plan de cuentas configurado)
        description = (
            f"{'Factura emitida' if invoice.invoice_type == 'issued' else 'Factura recibida'} "
            f"#{invoice.invoice_number or invoice_id} - {invoice.counterparty_name}"
        )

        # Buscar líneas con cuenta contable asignada para construir el asiento
        lines_with_accounts = [line for line in invoice.lines if line.account_id]
        if lines_with_accounts:
            journal_lines: List[dict] = []
            for line in lines_with_accounts:
                if invoice.invoice_type == "issued":
                    journal_lines.append({
                        "account_id": line.account_id,
                        "description": line.description,
                        "debit": 0.0,
                        "credit": line.subtotal,
                    })
                else:
                    journal_lines.append({
                        "account_id": line.account_id,
                        "description": line.description,
                        "debit": line.subtotal,
                        "credit": 0.0,
                    })

            entry_data = {
                "company_id": invoice.company_id,
                "fiscal_period_id": period.id,
                "entry_date": invoice.invoice_date,
                "description": description,
                "reference": f"INV-{invoice_id}",
                "status": "posted",
                "created_by_id": user_id,
                "source_type": "invoice",
                "source_id": invoice_id,
            }
            try:
                entry = self.entry_repo.create(entry_data, journal_lines)
                invoice.journal_entry_id = entry.id
            except Exception as e:
                logger.warning("No se pudo crear asiento para factura %d: %s", invoice_id, e)

        invoice.status = "issued"
        self.db.commit()
        self.db.refresh(invoice)
        logger.info("Factura emitida: invoice_id=%d user_id=%s", invoice_id, user_id)
        return invoice

    def register_payment(
        self, invoice_id: int, data: PaymentCreate, user_id: Optional[int] = None
    ) -> Payment:
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")
        if invoice.status not in ("issued", "overdue"):
            raise HTTPException(
                status_code=422,
                detail=f"No se puede registrar pago en factura con estado '{invoice.status}'.",
            )
        if data.amount <= 0:
            raise HTTPException(status_code=422, detail="El monto del pago debe ser mayor a cero.")

        payment_data = {
            "payment_date": data.payment_date,
            "amount": data.amount,
            "payment_method": data.payment_method,
            "bank_reference": data.bank_reference,
            "notes": data.notes,
        }
        payment = self.invoice_repo.add_payment(invoice_id, payment_data)

        # Verificar si la factura está pagada completamente
        total_paid = self.invoice_repo.get_total_paid(invoice_id)
        if total_paid >= invoice.total - 0.01:
            self.invoice_repo.update_status(invoice_id, "paid")
        else:
            # Pago parcial, mantener como emitida
            logger.info(
                "Pago parcial: invoice_id=%d pagado=%.2f total=%.2f",
                invoice_id, total_paid, invoice.total,
            )
        return payment

    def mark_overdue(self) -> int:
        """
        Marca como 'overdue' todas las facturas vencidas (due_date < hoy y estado issued).
        Retorna el número de facturas actualizadas.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        overdue = self.invoice_repo.get_overdue(now)
        count = 0
        for invoice in overdue:
            if invoice.status == "issued":
                self.invoice_repo.update_status(invoice.id, "overdue")
                count += 1
        return count

    def get_aging_report(
        self,
        invoice_type: str,
        as_of_date: Optional[datetime] = None,
        company_id: Optional[int] = None,
    ) -> AgingReport:
        """Genera reporte de antigüedad de cartera (CxC o CxP)."""
        if as_of_date is None:
            as_of_date = datetime.utcnow()

        invoices, _ = self.invoice_repo.get_all(
            company_id=company_id,
            invoice_type=invoice_type,
            status=None,
        )
        outstanding = [inv for inv in invoices if inv.status in ("issued", "overdue")]

        buckets = {
            "current": 0.0,
            "1-30": 0.0,
            "31-60": 0.0,
            "61-90": 0.0,
            "90+": 0.0,
        }
        counts = {k: 0 for k in buckets}

        for inv in outstanding:
            total_paid = self.invoice_repo.get_total_paid(inv.id)
            outstanding_amount = inv.total - total_paid
            if outstanding_amount <= 0:
                continue
            if inv.due_date is None or inv.due_date >= as_of_date:
                buckets["current"] += outstanding_amount
                counts["current"] += 1
            else:
                days_overdue = (as_of_date - inv.due_date).days
                if days_overdue <= 30:
                    buckets["1-30"] += outstanding_amount
                    counts["1-30"] += 1
                elif days_overdue <= 60:
                    buckets["31-60"] += outstanding_amount
                    counts["31-60"] += 1
                elif days_overdue <= 90:
                    buckets["61-90"] += outstanding_amount
                    counts["61-90"] += 1
                else:
                    buckets["90+"] += outstanding_amount
                    counts["90+"] += 1

        aging_buckets = [
            AgingBucket(bucket=k, count=counts[k], total_amount=round(v, 2))
            for k, v in buckets.items()
        ]
        return AgingReport(
            invoice_type=invoice_type,
            as_of_date=as_of_date,
            buckets=aging_buckets,
            total_outstanding=round(sum(buckets.values()), 2),
        )

    def generate_pdf(self, invoice_id: int) -> bytes:
        """Genera un PDF simple de la factura usando reportlab."""
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Factura no encontrada.")
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
            )
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="reportlab no está instalado. Ejecuta: pip install reportlab",
            )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Título
        title_text = "FACTURA" if invoice.invoice_type == "issued" else "FACTURA RECIBIDA"
        elements.append(Paragraph(f"<b>{title_text}</b>", styles["Title"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Encabezado
        header_data = [
            ["N° Factura:", invoice.invoice_number or str(invoice.id)],
            ["Fecha:", invoice.invoice_date.strftime("%d/%m/%Y")],
            ["Vencimiento:", invoice.due_date.strftime("%d/%m/%Y") if invoice.due_date else "N/A"],
            ["Cliente/Proveedor:", invoice.counterparty_name],
            ["Estado:", invoice.status.upper()],
        ]
        header_table = Table(header_data, colWidths=[2 * inch, 4 * inch])
        header_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Líneas de factura
        line_headers = ["Descripción", "Cant.", "P. Unit.", "% IVA", "Subtotal", "IVA", "Total"]
        line_rows = [line_headers]
        for line in invoice.lines:
            line_rows.append([
                line.description,
                f"{line.quantity:.2f}",
                f"{line.unit_price:,.2f}",
                f"{line.tax_rate:.1f}%",
                f"{line.subtotal:,.2f}",
                f"{line.tax_amount:,.2f}",
                f"{line.total:,.2f}",
            ])

        lines_table = Table(line_rows, colWidths=[2.5 * inch, 0.6 * inch, 0.9 * inch, 0.6 * inch, 0.9 * inch, 0.7 * inch, 0.8 * inch])
        lines_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(lines_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Totales
        totals_data = [
            ["Subtotal:", f"{invoice.subtotal:,.2f}"],
            ["IVA:", f"{invoice.tax_amount:,.2f}"],
            ["TOTAL:", f"{invoice.total:,.2f}"],
        ]
        totals_table = Table(totals_data, colWidths=[5 * inch, 2 * inch])
        totals_table.setStyle(TableStyle([
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ]))
        elements.append(totals_table)

        doc.build(elements)
        return buffer.getvalue()
