"""
Servicio de reportes financieros.

Genera los tres estados financieros fundamentales:
  - Estado de resultados (P&G)
  - Balance general
  - Flujo de caja (método indirecto simplificado)
"""
import io
import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.models import ChartOfAccount, JournalEntry, JournalEntryLine
from app.schemas.schemas import (
    IncomeStatementReport, IncomeStatementSection, IncomeStatementLine,
    BalanceSheetReport, BalanceSheetSection,
    CashFlowReport, CashFlowItem,
)
from app.repositories.repositories import (
    JournalEntryRepository, FiscalPeriodRepository, ChartOfAccountRepository,
)

logger = logging.getLogger(__name__)

# Tipos de cuenta y su clasificación
INCOME_TYPES = {"income"}
EXPENSE_TYPES = {"expense"}
ASSET_TYPES = {"asset"}
LIABILITY_TYPES = {"liability"}
EQUITY_TYPES = {"equity"}


def _net_balance(account_type: str, debit: float, credit: float) -> float:
    """Calcula el saldo neto según el tipo de cuenta."""
    if account_type in ASSET_TYPES | EXPENSE_TYPES:
        return debit - credit      # saldo normal deudor
    else:
        return credit - debit      # saldo normal acreedor


class FinancialReportService:
    def __init__(self, db: Session):
        self.db = db
        self.entry_repo = JournalEntryRepository(db)
        self.period_repo = FiscalPeriodRepository(db)
        self.account_repo = ChartOfAccountRepository(db)

    def _get_period_name(self, fiscal_period_id: int) -> str:
        period = self.period_repo.get_by_id(fiscal_period_id)
        return period.name if period else str(fiscal_period_id)

    def get_income_statement(
        self,
        fiscal_period_id: int,
        company_id: Optional[int] = None,
        compare_period_id: Optional[int] = None,
    ) -> IncomeStatementReport:
        """Estado de resultados: Ingresos − Gastos = Utilidad neta."""
        rows = self.entry_repo.get_trial_balance(company_id, fiscal_period_id)

        compare_rows = {}
        if compare_period_id:
            for row in self.entry_repo.get_trial_balance(company_id, compare_period_id):
                compare_rows[row["account_id"]] = row

        revenue_lines: List[IncomeStatementLine] = []
        expense_lines: List[IncomeStatementLine] = []

        for row in rows:
            net = _net_balance(row["account_type"], row["total_debit"], row["total_credit"])
            compare_net = None
            if compare_period_id and row["account_id"] in compare_rows:
                cr = compare_rows[row["account_id"]]
                compare_net = _net_balance(cr["account_type"], cr["total_debit"], cr["total_credit"])

            line = IncomeStatementLine(
                account_code=row["account_code"],
                account_name=row["account_name"],
                amount=round(net, 2),
                compare_amount=round(compare_net, 2) if compare_net is not None else None,
            )
            if row["account_type"] in INCOME_TYPES:
                revenue_lines.append(line)
            elif row["account_type"] in EXPENSE_TYPES:
                expense_lines.append(line)

        total_revenues = sum(l.amount for l in revenue_lines)
        total_expenses = sum(l.amount for l in expense_lines)
        net_income = total_revenues - total_expenses

        compare_revenues = None
        compare_expenses = None
        compare_net_income = None
        if compare_period_id:
            compare_revenues = sum((l.compare_amount or 0) for l in revenue_lines)
            compare_expenses = sum((l.compare_amount or 0) for l in expense_lines)
            compare_net_income = compare_revenues - compare_expenses

        return IncomeStatementReport(
            period_name=self._get_period_name(fiscal_period_id),
            compare_period_name=self._get_period_name(compare_period_id) if compare_period_id else None,
            revenues=IncomeStatementSection(
                name="Ingresos",
                lines=revenue_lines,
                total=round(total_revenues, 2),
                compare_total=round(compare_revenues, 2) if compare_revenues is not None else None,
            ),
            expenses=IncomeStatementSection(
                name="Gastos y Costos",
                lines=expense_lines,
                total=round(total_expenses, 2),
                compare_total=round(compare_expenses, 2) if compare_expenses is not None else None,
            ),
            net_income=round(net_income, 2),
            compare_net_income=round(compare_net_income, 2) if compare_net_income is not None else None,
        )

    def get_balance_sheet(
        self,
        fiscal_period_id: int,
        company_id: Optional[int] = None,
    ) -> BalanceSheetReport:
        """
        Balance general. Acumula saldos de todos los períodos hasta el especificado.
        Ecuación contable: Activos = Pasivos + Patrimonio.
        """
        # Para el balance, consideramos TODOS los asientos publicados hasta la fecha del período
        period = self.period_repo.get_by_id(fiscal_period_id)
        if not period:
            raise HTTPException(status_code=404, detail="Período fiscal no encontrado.")

        # Obtener trial balance acumulado (sin filtro de período = todos los períodos)
        rows = self.entry_repo.get_trial_balance(company_id, fiscal_period_id=None)

        assets_current_lines: List[IncomeStatementLine] = []
        assets_nc_lines: List[IncomeStatementLine] = []
        liabilities_current_lines: List[IncomeStatementLine] = []
        liabilities_nc_lines: List[IncomeStatementLine] = []
        equity_lines: List[IncomeStatementLine] = []

        for row in rows:
            if row["account_type"] not in ASSET_TYPES | LIABILITY_TYPES | EQUITY_TYPES:
                continue
            net = _net_balance(row["account_type"], row["total_debit"], row["total_credit"])
            line = IncomeStatementLine(
                account_code=row["account_code"],
                account_name=row["account_name"],
                amount=round(net, 2),
            )
            # Clasificación por nivel de cuenta (nivel 1 = corriente, nivel 2+ = no corriente)
            # Simplificación: usar "corriente" para todos los activos/pasivos por defecto.
            # En producción, usar campos is_current en la cuenta.
            if row["account_type"] == "asset":
                assets_current_lines.append(line)
            elif row["account_type"] == "liability":
                liabilities_current_lines.append(line)
            elif row["account_type"] == "equity":
                equity_lines.append(line)

        total_assets_c = sum(l.amount for l in assets_current_lines)
        total_assets_nc = sum(l.amount for l in assets_nc_lines)
        total_assets = total_assets_c + total_assets_nc
        total_liab_c = sum(l.amount for l in liabilities_current_lines)
        total_liab_nc = sum(l.amount for l in liabilities_nc_lines)
        total_liabilities = total_liab_c + total_liab_nc
        total_equity = sum(l.amount for l in equity_lines)

        balanced = abs(total_assets - (total_liabilities + total_equity)) < 0.05

        return BalanceSheetReport(
            period_name=period.name,
            assets_current=BalanceSheetSection(name="Activos Corrientes", lines=assets_current_lines, total=round(total_assets_c, 2)),
            assets_non_current=BalanceSheetSection(name="Activos No Corrientes", lines=assets_nc_lines, total=round(total_assets_nc, 2)),
            total_assets=round(total_assets, 2),
            liabilities_current=BalanceSheetSection(name="Pasivos Corrientes", lines=liabilities_current_lines, total=round(total_liab_c, 2)),
            liabilities_non_current=BalanceSheetSection(name="Pasivos No Corrientes", lines=liabilities_nc_lines, total=round(total_liab_nc, 2)),
            total_liabilities=round(total_liabilities, 2),
            equity=BalanceSheetSection(name="Patrimonio", lines=equity_lines, total=round(total_equity, 2)),
            total_equity=round(total_equity, 2),
            balanced=balanced,
        )

    def get_cash_flow(
        self,
        fiscal_period_id: int,
        company_id: Optional[int] = None,
    ) -> CashFlowReport:
        """Flujo de caja por método indirecto (simplificado)."""
        period = self.period_repo.get_by_id(fiscal_period_id)
        if not period:
            raise HTTPException(status_code=404, detail="Período fiscal no encontrado.")

        is_report = self.get_income_statement(fiscal_period_id, company_id)
        net_income = is_report.net_income

        # Actividades operativas: utilidad neta + ajustes no monetarios (simplificado)
        operating: List[CashFlowItem] = [
            CashFlowItem(label="Utilidad neta del período", amount=net_income),
        ]

        # Ajustes por ingresos/gastos por cuenta
        for line in is_report.revenues.lines:
            if line.amount != 0:
                operating.append(CashFlowItem(label=f"Ingreso - {line.account_name}", amount=-line.amount))
        for line in is_report.expenses.lines:
            if line.amount != 0:
                operating.append(CashFlowItem(label=f"Gasto - {line.account_name}", amount=line.amount))

        # Actividades de inversión y financiamiento (vacías sin datos adicionales)
        investing: List[CashFlowItem] = []
        financing: List[CashFlowItem] = []

        net_operating = sum(item.amount for item in operating)
        net_investing = sum(item.amount for item in investing)
        net_financing = sum(item.amount for item in financing)

        return CashFlowReport(
            period_name=period.name,
            operating=operating,
            investing=investing,
            financing=financing,
            net_operating=round(net_operating, 2),
            net_investing=round(net_investing, 2),
            net_financing=round(net_financing, 2),
            net_change=round(net_operating + net_investing + net_financing, 2),
        )

    def to_excel(
        self,
        fiscal_period_id: int,
        report_type: str,
        company_id: Optional[int] = None,
    ) -> bytes:
        """Exporta un reporte a Excel con múltiples hojas."""
        import xlsxwriter
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer)

        header_fmt = workbook.add_format({"bold": True, "bg_color": "#2563EB", "font_color": "white"})
        total_fmt = workbook.add_format({"bold": True, "border": 1})
        money_fmt = workbook.add_format({"num_format": "#,##0.00"})
        money_bold = workbook.add_format({"bold": True, "num_format": "#,##0.00"})

        if report_type == "income_statement":
            report = self.get_income_statement(fiscal_period_id, company_id)
            ws = workbook.add_worksheet("Estado de Resultados")
            ws.write(0, 0, f"Estado de Resultados - {report.period_name}", header_fmt)
            row = 2
            ws.write(row, 0, "INGRESOS", workbook.add_format({"bold": True}))
            row += 1
            for line in report.revenues.lines:
                ws.write(row, 1, line.account_code)
                ws.write(row, 2, line.account_name)
                ws.write(row, 3, line.amount, money_fmt)
                row += 1
            ws.write(row, 2, "Total Ingresos", total_fmt)
            ws.write(row, 3, report.revenues.total, money_bold)
            row += 2
            ws.write(row, 0, "GASTOS", workbook.add_format({"bold": True}))
            row += 1
            for line in report.expenses.lines:
                ws.write(row, 1, line.account_code)
                ws.write(row, 2, line.account_name)
                ws.write(row, 3, line.amount, money_fmt)
                row += 1
            ws.write(row, 2, "Total Gastos", total_fmt)
            ws.write(row, 3, report.expenses.total, money_bold)
            row += 2
            ws.write(row, 2, "UTILIDAD NETA", total_fmt)
            ws.write(row, 3, report.net_income, money_bold)

        elif report_type == "balance_sheet":
            report = self.get_balance_sheet(fiscal_period_id, company_id)
            ws = workbook.add_worksheet("Balance General")
            ws.write(0, 0, f"Balance General - {report.period_name}", header_fmt)
            row = 2
            for section_name, section in [
                ("ACTIVOS CORRIENTES", report.assets_current),
                ("ACTIVOS NO CORRIENTES", report.assets_non_current),
                ("PASIVOS CORRIENTES", report.liabilities_current),
                ("PASIVOS NO CORRIENTES", report.liabilities_non_current),
                ("PATRIMONIO", report.equity),
            ]:
                ws.write(row, 0, section_name, workbook.add_format({"bold": True}))
                row += 1
                for line in section.lines:
                    ws.write(row, 1, line.account_code)
                    ws.write(row, 2, line.account_name)
                    ws.write(row, 3, line.amount, money_fmt)
                    row += 1
                ws.write(row, 2, f"Total {section.name}", total_fmt)
                ws.write(row, 3, section.total, money_bold)
                row += 2

        workbook.close()
        return buffer.getvalue()
