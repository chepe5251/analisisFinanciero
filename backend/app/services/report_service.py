"""
Servicio de generación de reportes.
Produce DataFrames de pandas que los endpoints convierten a CSV o Excel.

Supuesto: los reportes se generan en memoria (BytesIO) para no depender de disco.
Para volúmenes grandes esto debería moverse a generación asíncrona con cola de tareas.
"""
import io
from typing import List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.models.models import ReconciliationResult, EmployeeTemplate, BankTransaction
from app.repositories.repositories import ReconciliationResultRepository


# Columnas y etiquetas de cada tipo de reporte
COLUMN_LABELS = {
    "id": "ID",
    "reconciliation_status": "Estado",
    "employee_name": "Empleado",
    "bank_name": "Banco",
    "account_number": "Cuenta",
    "expected_amount": "Monto Esperado",
    "reported_amount": "Monto Reportado",
    "difference_amount": "Diferencia",
    "matched_by": "Método de Match",
    "notes": "Notas",
    "created_at": "Fecha Proceso",
}

STATUS_LABELS = {
    "matched": "Conciliado",
    "difference": "Diferencia de Monto",
    "missing": "Faltante en Banco",
    "extra": "Sobrante en Banco",
    "duplicate": "Posible Duplicado",
    "pending": "Pendiente Revisión",
}


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.result_repo = ReconciliationResultRepository(db)

    def _results_to_df(self, results: List[ReconciliationResult]) -> pd.DataFrame:
        """Convierte lista de resultados ORM a DataFrame limpio."""
        rows = []
        for r in results:
            rows.append({
                "id": r.id,
                "reconciliation_status": STATUS_LABELS.get(r.reconciliation_status, r.reconciliation_status),
                "employee_name": r.employee_name or "",
                "bank_name": r.bank_name or "",
                "account_number": r.account_number or "",
                "expected_amount": r.expected_amount,
                "reported_amount": r.reported_amount,
                "difference_amount": r.difference_amount,
                "matched_by": r.matched_by or "",
                "notes": r.notes or "",
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            })

        df = pd.DataFrame(rows)
        if df.empty:
            df = pd.DataFrame(columns=list(COLUMN_LABELS.keys()))
        df = df.rename(columns=COLUMN_LABELS)
        return df

    def generate_consolidated_csv(self) -> bytes:
        """Reporte completo de todos los resultados."""
        results = self.result_repo.get_all()
        df = self._results_to_df(results)
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    def generate_inconsistencies_csv(self) -> bytes:
        """Solo registros que requieren atención (no-matched)."""
        results = self.result_repo.get_inconsistencies()
        df = self._results_to_df(results)
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    def generate_missing_csv(self) -> bytes:
        """Empleados en plantilla sin transacción bancaria."""
        all_results = self.result_repo.get_all()
        results = [r for r in all_results if r.reconciliation_status == "missing"]
        df = self._results_to_df(results)
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    def generate_extras_csv(self) -> bytes:
        """Transacciones bancarias sin empleado en plantilla."""
        all_results = self.result_repo.get_all()
        results = [r for r in all_results if r.reconciliation_status == "extra"]
        df = self._results_to_df(results)
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    def generate_consolidated_excel(self) -> bytes:
        """
        Reporte Excel con múltiples hojas:
        - Resumen (KPIs)
        - Todos los resultados
        - Inconsistencias
        - Faltantes
        - Sobrantes
        """
        all_results = self.result_repo.get_all()
        summary_data = self.result_repo.get_summary()

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            # Hoja: Resumen
            summary_rows = [
                {"Indicador": "Total procesados", "Valor": summary_data["total_processed"]},
                {"Indicador": "Conciliados", "Valor": summary_data["total_matched"]},
                {"Indicador": "Con diferencia", "Valor": summary_data["total_difference"]},
                {"Indicador": "Faltantes", "Valor": summary_data["total_missing"]},
                {"Indicador": "Sobrantes", "Valor": summary_data["total_extra"]},
                {"Indicador": "Duplicados", "Valor": summary_data["total_duplicate"]},
                {"Indicador": "Monto esperado total", "Valor": summary_data["total_expected_amount"]},
                {"Indicador": "Monto reportado total", "Valor": summary_data["total_reported_amount"]},
                {"Indicador": "Monto conciliado", "Valor": summary_data["total_matched_amount"]},
                {"Indicador": "Monto con diferencias", "Valor": summary_data["total_difference_amount"]},
            ]
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Resumen", index=False)

            # Hoja: Todos
            self._results_to_df(all_results).to_excel(writer, sheet_name="Todos", index=False)

            # Hoja: Inconsistencias
            inconsistencies = [r for r in all_results if r.reconciliation_status != "matched"]
            self._results_to_df(inconsistencies).to_excel(writer, sheet_name="Inconsistencias", index=False)

            # Hoja: Faltantes
            missing = [r for r in all_results if r.reconciliation_status == "missing"]
            self._results_to_df(missing).to_excel(writer, sheet_name="Faltantes", index=False)

            # Hoja: Sobrantes
            extras = [r for r in all_results if r.reconciliation_status == "extra"]
            self._results_to_df(extras).to_excel(writer, sheet_name="Sobrantes", index=False)

        return buffer.getvalue()
