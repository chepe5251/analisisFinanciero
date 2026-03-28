"""
Endpoints del dashboard financiero extendido.

GET /dashboard/financial-kpis   KPIs del período activo
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import User
from app.schemas.schemas import FinancialKPIs
from app.repositories.repositories import (
    FiscalPeriodRepository, JournalEntryRepository,
    BudgetRepository, InvoiceRepository,
)
from app.services.financial_report_service import FinancialReportService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/financial-kpis", response_model=FinancialKPIs)
def get_financial_kpis(
    company_id: Optional[int] = Query(None),
    fiscal_period_id: Optional[int] = Query(None, description="Si se omite, usa el período abierto más reciente"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    KPIs financieros del período activo:
    - Liquidez corriente
    - Capital de trabajo
    - Margen de utilidad neta
    - Días de cuentas por cobrar
    - Ejecución presupuestaria
    - Facturas vencidas
    """
    period_repo = FiscalPeriodRepository(db)

    # Determinar período a usar
    if fiscal_period_id:
        period = period_repo.get_by_id(fiscal_period_id)
    else:
        open_periods = period_repo.get_open(company_id)
        period = open_periods[0] if open_periods else None

    if not period:
        return FinancialKPIs(period_name="Sin período activo")

    period_name = period.name
    report_svc = FinancialReportService(db)
    invoice_repo = InvoiceRepository(db)
    budget_repo = BudgetRepository(db)

    # Balance sheet para ratios de liquidez
    try:
        bs = report_svc.get_balance_sheet(period.id, company_id)
        total_assets_current = bs.assets_current.total
        total_liab_current = bs.liabilities_current.total
        current_ratio = (
            round(total_assets_current / total_liab_current, 2)
            if total_liab_current > 0 else None
        )
        working_capital = round(total_assets_current - total_liab_current, 2)
    except Exception:
        current_ratio = None
        working_capital = None

    # Income statement para margen
    try:
        is_report = report_svc.get_income_statement(period.id, company_id)
        total_revenues = is_report.revenues.total
        total_expenses = is_report.expenses.total
        net_income = is_report.net_income
        net_profit_margin = (
            round(net_income / total_revenues * 100, 2)
            if total_revenues > 0 else None
        )
    except Exception:
        total_revenues = 0.0
        total_expenses = 0.0
        net_income = 0.0
        net_profit_margin = None

    # Facturas vencidas
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    overdue_invoices = invoice_repo.get_overdue(now, company_id)
    overdue_count = len(overdue_invoices)
    overdue_amount = sum(inv.total for inv in overdue_invoices)

    # CxC total
    issued_invoices, _ = invoice_repo.get_all(
        company_id=company_id,
        invoice_type="issued",
        status="issued",
    )
    total_receivables = sum(inv.total for inv in issued_invoices)
    received_invoices, _ = invoice_repo.get_all(
        company_id=company_id,
        invoice_type="received",
        status="issued",
    )
    total_payables = sum(inv.total for inv in received_invoices)

    # Días de CxC
    days_receivable = None
    if total_revenues > 0 and total_receivables > 0:
        daily_sales = total_revenues / 30
        if daily_sales > 0:
            days_receivable = round(total_receivables / daily_sales, 1)

    # Ejecución presupuestaria
    budget_execution_pct = None
    try:
        budgets = budget_repo.get_all(company_id)
        period_budgets = [b for b in budgets if b.fiscal_period_id == period.id and b.status == "approved"]
        if period_budgets:
            total_planned = 0.0
            total_executed = 0.0
            for budget in period_budgets:
                for line in budget.lines:
                    planned = line.planned_amount
                    executed = budget_repo.get_executed_amount(budget.id, line.account_id)
                    total_planned += planned
                    total_executed += executed
            if total_planned > 0:
                budget_execution_pct = round(total_executed / total_planned * 100, 2)
    except Exception:
        pass

    return FinancialKPIs(
        period_name=period_name,
        current_ratio=current_ratio,
        working_capital=working_capital,
        net_profit_margin=net_profit_margin,
        days_receivable=days_receivable,
        budget_execution_pct=budget_execution_pct,
        overdue_invoices_count=overdue_count,
        overdue_invoices_amount=round(overdue_amount, 2),
        total_revenues=round(total_revenues, 2),
        total_expenses=round(total_expenses, 2),
        net_income=round(net_income, 2),
        total_receivables=round(total_receivables, 2),
        total_payables=round(total_payables, 2),
    )
