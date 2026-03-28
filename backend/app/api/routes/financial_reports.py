"""
Endpoints de reportes financieros.

GET    /reports/income-statement          Estado de resultados
GET    /reports/balance-sheet             Balance general
GET    /reports/cash-flow                 Flujo de caja
GET    /reports/income-statement/excel    Exportar Excel
GET    /reports/balance-sheet/excel       Exportar Excel
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.models import User
from app.schemas.schemas import IncomeStatementReport, BalanceSheetReport, CashFlowReport
from app.services.financial_report_service import FinancialReportService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/financial-reports", tags=["financial-reports"])

_view = require_permission("reports", "view")
_export = require_permission("reports", "export")


@router.get("/income-statement", response_model=IncomeStatementReport)
def get_income_statement(
    fiscal_period_id: int = Query(..., description="ID del período fiscal"),
    company_id: Optional[int] = Query(None),
    compare_period_id: Optional[int] = Query(None, description="Período de comparación (opcional)"),
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """
    Estado de resultados (P&G) para un período.
    Soporta comparación con otro período (ej: mes anterior).
    """
    svc = FinancialReportService(db)
    return svc.get_income_statement(fiscal_period_id, company_id, compare_period_id)


@router.get("/balance-sheet", response_model=BalanceSheetReport)
def get_balance_sheet(
    fiscal_period_id: int = Query(..., description="ID del período fiscal"),
    company_id: Optional[int] = Query(None),
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """
    Balance general al cierre del período.
    Valida la ecuación contable: Activos = Pasivos + Patrimonio.
    """
    svc = FinancialReportService(db)
    return svc.get_balance_sheet(fiscal_period_id, company_id)


@router.get("/cash-flow", response_model=CashFlowReport)
def get_cash_flow(
    fiscal_period_id: int = Query(..., description="ID del período fiscal"),
    company_id: Optional[int] = Query(None),
    current_user: User = Depends(_view),
    db: Session = Depends(get_db),
):
    """Flujo de caja por método indirecto."""
    svc = FinancialReportService(db)
    return svc.get_cash_flow(fiscal_period_id, company_id)


@router.get("/income-statement/excel")
def export_income_statement_excel(
    fiscal_period_id: int = Query(...),
    company_id: Optional[int] = Query(None),
    current_user: User = Depends(_export),
    db: Session = Depends(get_db),
):
    """Exporta el estado de resultados como archivo Excel."""
    svc = FinancialReportService(db)
    excel_bytes = svc.to_excel(fiscal_period_id, "income_statement", company_id)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=estado_resultados_p{fiscal_period_id}.xlsx"},
    )


@router.get("/balance-sheet/excel")
def export_balance_sheet_excel(
    fiscal_period_id: int = Query(...),
    company_id: Optional[int] = Query(None),
    current_user: User = Depends(_export),
    db: Session = Depends(get_db),
):
    """Exporta el balance general como archivo Excel."""
    svc = FinancialReportService(db)
    excel_bytes = svc.to_excel(fiscal_period_id, "balance_sheet", company_id)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=balance_general_p{fiscal_period_id}.xlsx"},
    )
