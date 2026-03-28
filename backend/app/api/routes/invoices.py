"""
Endpoints de facturación.

POST   /invoices                   Crear factura
GET    /invoices                   Listar con filtros
GET    /invoices/{id}              Detalle de factura
POST   /invoices/{id}/issue        Emitir factura (genera asiento)
POST   /invoices/{id}/payments     Registrar pago
GET    /invoices/{id}/pdf          Descargar PDF
GET    /invoices/aging             Reporte de antigüedad
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.models import User
from app.schemas.schemas import (
    InvoiceCreate, InvoiceOut, PaymentCreate, PaymentOut, AgingReport,
)
from app.services.invoice_service import InvoiceService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/invoices", tags=["invoices"])

_view = require_permission("invoices", "view")
_create = require_permission("invoices", "create")
_issue = require_permission("invoices", "issue")


@router.get("/aging", response_model=AgingReport)
def get_aging_report(
    invoice_type: str = Query("issued", description="issued (CxC) | received (CxP)"),
    company_id: Optional[int] = Query(None),
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """
    Reporte de antigüedad de cartera.
    Clasifica facturas pendientes de cobro/pago por rango de días vencidos.
    """
    svc = InvoiceService(db)
    return svc.get_aging_report(invoice_type, company_id=company_id)


@router.post("", response_model=InvoiceOut, status_code=201)
def create_invoice(
    body: InvoiceCreate,
    current_user: User = Depends(_create),
    db: Session = Depends(get_db),
):
    """Crea una factura en estado borrador con cálculo automático de totales."""
    svc = InvoiceService(db)
    invoice = svc.create_invoice(body, created_by_id=current_user.id)
    return InvoiceOut.model_validate(invoice)


@router.get("", response_model=dict)
def list_invoices(
    invoice_type: Optional[str] = Query(None, description="issued | received"),
    status: Optional[str] = Query(None, description="draft|issued|paid|overdue|voided"),
    company_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """Lista facturas con filtros opcionales por tipo y estado."""
    from app.repositories.repositories import InvoiceRepository
    repo = InvoiceRepository(db)
    # Mark overdue before listing
    svc = InvoiceService(db)
    svc.mark_overdue()
    offset = (page - 1) * page_size
    items, total = repo.get_all(
        company_id=company_id,
        invoice_type=invoice_type,
        status=status,
        offset=offset,
        limit=page_size,
    )
    return {
        "items": [InvoiceOut.model_validate(i) for i in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    from app.repositories.repositories import InvoiceRepository
    invoice = InvoiceRepository(db).get_by_id(invoice_id)
    if not invoice:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Factura no encontrada.")
    return InvoiceOut.model_validate(invoice)


@router.post("/{invoice_id}/issue", response_model=InvoiceOut)
def issue_invoice(
    invoice_id: int,
    current_user: User = Depends(_issue),
    db: Session = Depends(get_db),
):
    """
    Emite la factura y genera automáticamente el asiento contable.
    Requiere que exista al menos un período fiscal abierto.
    """
    svc = InvoiceService(db)
    invoice = svc.issue_invoice(invoice_id, user_id=current_user.id)
    return InvoiceOut.model_validate(invoice)


@router.post("/{invoice_id}/payments", response_model=PaymentOut, status_code=201)
def register_payment(
    invoice_id: int,
    body: PaymentCreate,
    current_user: User = Depends(_create),
    db: Session = Depends(get_db),
):
    """Registra un pago parcial o total de la factura."""
    svc = InvoiceService(db)
    payment = svc.register_payment(invoice_id, body, user_id=current_user.id)
    return PaymentOut.model_validate(payment)


@router.get("/{invoice_id}/pdf")
def download_pdf(
    invoice_id: int,
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """Descarga la factura en formato PDF."""
    svc = InvoiceService(db)
    pdf_bytes = svc.generate_pdf(invoice_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=factura_{invoice_id}.pdf"},
    )
