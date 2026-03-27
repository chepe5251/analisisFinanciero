"""
Servicio de conciliación financiera.

Lógica de matching (en orden de prioridad):
  1. Cuenta bancaria exacta + mismo banco  →  matched / difference
  2. employee_id encontrado en campo reference  →  matched / difference
  3. Nombre normalizado (similitud ≥ umbral) + mismo banco  →  matched / difference
  4. Empleados sin match  →  missing
  5. Transacciones sin match  →  extra
  6. Más de una transacción para la misma cuenta en el mismo archivo  →  duplicate

Supuestos:
  - La plantilla es la fuente de verdad.
  - Un empleado puede tener solo un pago esperado por corrida.
  - Si hay diferencia de monto ≤ AMOUNT_TOLERANCE se considera 'matched'.
  - La detección de duplicados es dentro del mismo archivo bancario.
"""
import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.models import EmployeeTemplate, BankTransaction
from app.schemas.schemas import (
    EmployeeTemplateCreate, BankTransactionCreate,
    ReconciliationResultCreate, ReconciliationSummary,
    ReconciliationRunRequest, ReconciliationRunResult,
)
from app.utils.file_processor import FileProcessor, TEMPLATE_COLUMN_MAPPINGS
from app.repositories.repositories import (
    EmployeeTemplateRepository, BankTransactionRepository,
    ReconciliationResultRepository, ReconciliationBatchRepository,
)
from app.core.config import settings

import pandas as pd

logger = logging.getLogger(__name__)


class ProcessingStats:
    """Agrupa estadísticas del procesamiento de un archivo."""
    def __init__(self):
        self.total: int = 0
        self.processed: int = 0
        self.errors: int = 0
        self.error_details: List[str] = []

    def add_error(self, row_index: int, reason: str) -> None:
        self.errors += 1
        self.error_details.append(f"Fila {row_index}: {reason}")

    def summary_message(self) -> str:
        parts = [f"{self.processed} registros procesados"]
        if self.errors:
            parts.append(f"{self.errors} filas omitidas con error")
        return ", ".join(parts)


class ReconciliationService:
    def __init__(self, db: Session):
        self.db = db
        self.template_repo = EmployeeTemplateRepository(db)
        self.transaction_repo = BankTransactionRepository(db)
        self.result_repo = ReconciliationResultRepository(db)
        self.batch_repo = ReconciliationBatchRepository(db)

    # ------------------------------------------------------------------
    # Procesamiento de archivos
    # ------------------------------------------------------------------

    def process_employee_template(
        self, upload_id: int, file_path: str
    ) -> Tuple[List[EmployeeTemplate], ProcessingStats]:
        """
        Lee, valida y persiste la plantilla de personal.
        Retorna (registros guardados, estadísticas de procesamiento).
        """
        df = self._read_file(file_path)
        stats = ProcessingStats()
        stats.total = len(df)

        df = FileProcessor.normalize_columns(df, TEMPLATE_COLUMN_MAPPINGS)

        required = ["employee_id", "full_name", "bank_name", "account_number", "expected_amount"]
        missing_cols = FileProcessor.validate_required_columns(df, required)
        if missing_cols:
            raise ValueError(
                f"Columnas requeridas faltantes en plantilla: {missing_cols}. "
                f"Columnas encontradas: {list(df.columns)}"
            )

        templates: List[EmployeeTemplateCreate] = []
        for idx, row in df.iterrows():
            try:
                if pd.isna(row.get("employee_id")) or str(row.get("employee_id", "")).strip() == "":
                    stats.add_error(idx, "employee_id vacío")  # type: ignore[arg-type]
                    continue
                if pd.isna(row.get("full_name")) or str(row.get("full_name", "")).strip() == "":
                    stats.add_error(idx, "full_name vacío")  # type: ignore[arg-type]
                    continue

                templates.append(
                    EmployeeTemplateCreate(
                        upload_id=upload_id,
                        employee_id=str(row["employee_id"]).strip(),
                        full_name=str(row["full_name"]).strip(),
                        identification=(
                            str(row["identification"]).strip()
                            if pd.notna(row.get("identification")) else None
                        ),
                        bank_name=str(row["bank_name"]).strip(),
                        account_number=str(row["account_number"]).strip(),
                        expected_amount=FileProcessor.clean_amount(row["expected_amount"]),
                        currency=(
                            str(row["currency"]).strip()
                            if pd.notna(row.get("currency")) else "USD"
                        ),
                    )
                )
                stats.processed += 1
            except Exception as e:
                stats.add_error(idx, str(e))  # type: ignore[arg-type]

        records = self.template_repo.create_batch(templates)
        logger.info("Plantilla procesada: upload_id=%d %s", upload_id, stats.summary_message())
        return records, stats

    def process_bank_transactions(
        self, upload_id: int, file_path: str, bank_name: str
    ) -> Tuple[List[BankTransaction], ProcessingStats]:
        """
        Lee, valida y persiste transacciones bancarias.
        Retorna (registros guardados, estadísticas de procesamiento).
        """
        df = self._read_file(file_path)
        stats = ProcessingStats()
        stats.total = len(df)

        mapping = FileProcessor.get_bank_mapping(bank_name)
        df = FileProcessor.normalize_columns(df, mapping)

        required = ["beneficiary_name", "amount"]
        missing_cols = FileProcessor.validate_required_columns(df, required)
        if missing_cols:
            raise ValueError(
                f"Columnas requeridas faltantes en reporte de '{bank_name}': {missing_cols}. "
                f"Columnas detectadas: {list(df.columns)}. "
                f"Revisa que el nombre del banco corresponda al formato del archivo."
            )

        transactions: List[BankTransactionCreate] = []
        for idx, row in df.iterrows():
            try:
                name = row.get("beneficiary_name")
                amount = row.get("amount")

                if pd.isna(name) or str(name).strip() == "":
                    stats.add_error(idx, "beneficiary_name vacío")  # type: ignore[arg-type]
                    continue
                if pd.isna(amount) or str(amount).strip() == "":
                    stats.add_error(idx, "amount vacío")  # type: ignore[arg-type]
                    continue

                tx_date = None
                if "transaction_date" in row and pd.notna(row["transaction_date"]):
                    tx_date = FileProcessor.parse_date(str(row["transaction_date"]))

                account = (
                    str(row["beneficiary_account"]).strip()
                    if "beneficiary_account" in row and pd.notna(row.get("beneficiary_account"))
                    else None
                )
                ref = (
                    str(row["reference"]).strip()
                    if "reference" in row and pd.notna(row.get("reference"))
                    else None
                )

                transactions.append(
                    BankTransactionCreate(
                        upload_id=upload_id,
                        bank_name=bank_name,
                        transaction_date=tx_date,
                        beneficiary_name=str(name).strip(),
                        beneficiary_account=account,
                        amount=FileProcessor.clean_amount(amount),
                        currency=(
                            str(row["currency"]).strip()
                            if "currency" in row and pd.notna(row.get("currency"))
                            else "USD"
                        ),
                        reference=ref,
                        raw_data_json=row.to_dict(),
                    )
                )
                stats.processed += 1
            except Exception as e:
                stats.add_error(idx, str(e))  # type: ignore[arg-type]
                logger.warning("Fila omitida en %s fila %s: %s", bank_name, idx, e)

        records = self.transaction_repo.create_batch(transactions)
        logger.info("Banco %s procesado: upload_id=%d %s", bank_name, upload_id, stats.summary_message())
        return records, stats

    # ------------------------------------------------------------------
    # Conciliación
    # ------------------------------------------------------------------

    def run_reconciliation(self, request: ReconciliationRunRequest) -> "ReconciliationRunResult":
        """
        Ejecuta la conciliación completa.
        Limpia los resultados anteriores antes de cada corrida.
        Retorna (summary, batch_id).
        """
        templates = self.template_repo.get_by_upload_id(request.template_upload_id)
        if not templates:
            raise ValueError(
                f"No se encontraron registros de plantilla para upload_id="
                f"{request.template_upload_id}. "
                f"Asegúrate de haber subido y procesado la plantilla correctamente."
            )

        transactions: List[BankTransaction] = []
        missing_uploads: List[int] = []
        for uid in request.bank_upload_ids:
            batch = self.transaction_repo.get_by_upload_id(uid)
            if not batch:
                missing_uploads.append(uid)
            transactions.extend(batch)

        if missing_uploads:
            logger.warning("Uploads sin transacciones: %s", missing_uploads)

        if not transactions:
            raise ValueError(
                "No se encontraron transacciones bancarias. "
                "Verifica que los reportes bancarios hayan sido procesados."
            )

        # Limpiar corrida anterior
        self.result_repo.delete_all()

        # Ejecutar algoritmo
        results = self._perform_reconciliation(templates, transactions)

        # Persistir
        self.result_repo.create_batch(results)

        # Registrar batch
        batch = self.batch_repo.create(
            template_upload_id=request.template_upload_id,
            total_results=len(results),
        )

        summary_data = self.result_repo.get_summary()
        summary = ReconciliationSummary(**summary_data)

        logger.info(
            "Conciliación completada: batch_id=%d total=%d matched=%d missing=%d extra=%d",
            batch.id, len(results), summary.total_matched, summary.total_missing, summary.total_extra,
        )

        return ReconciliationRunResult(summary=summary, batch_id=batch.id)

    # ------------------------------------------------------------------
    # Algoritmo principal
    # ------------------------------------------------------------------

    def _perform_reconciliation(
        self,
        templates: List[EmployeeTemplate],
        transactions: List[BankTransaction],
    ) -> List[ReconciliationResultCreate]:
        """
        Algoritmo de conciliación en 3 pasadas + detección de duplicados.

        Pasada 1: match por número de cuenta + mismo banco
        Pasada 2: match por employee_id en campo reference
        Pasada 3: match por similitud de nombre + mismo banco
        Post:     missing, extra, duplicados
        """
        results: List[ReconciliationResultCreate] = []

        # Índices para búsqueda eficiente (O(1) en lugar de O(n) en cada iteración)
        by_account: Dict[Tuple[str, str], EmployeeTemplate] = {
            (t.account_number.strip(), t.bank_name.lower().strip()): t
            for t in templates
        }
        by_employee_id: Dict[str, EmployeeTemplate] = {
            t.employee_id: t for t in templates
        }

        matched_template_ids: Set[int] = set()
        matched_transaction_ids: Set[int] = set()

        # ----- Pasada 1: cuenta + banco (más confiable) -----
        for tx in transactions:
            if not tx.beneficiary_account:
                continue
            key = (tx.beneficiary_account.strip(), tx.bank_name.lower().strip())
            template = by_account.get(key)
            if template and template.id not in matched_template_ids:
                status, diff = self._compare_amounts(template.expected_amount, tx.amount)
                results.append(self._build_result(template, tx, status, diff, "account"))
                matched_template_ids.add(template.id)
                matched_transaction_ids.add(tx.id)

        # ----- Pasada 2: employee_id en reference -----
        for tx in transactions:
            if tx.id in matched_transaction_ids or not tx.reference:
                continue
            template = self._find_template_by_reference(tx.reference, by_employee_id, tx.bank_name)
            if template and template.id not in matched_template_ids:
                status, diff = self._compare_amounts(template.expected_amount, tx.amount)
                results.append(self._build_result(template, tx, status, diff, "employee_id_in_reference"))
                matched_template_ids.add(template.id)
                matched_transaction_ids.add(tx.id)

        # ----- Pasada 3: similitud de nombre + banco -----
        unmatched_templates = [t for t in templates if t.id not in matched_template_ids]
        unmatched_transactions = [tx for tx in transactions if tx.id not in matched_transaction_ids]

        for template in unmatched_templates:
            best_tx, best_score = self._find_best_name_match(template, unmatched_transactions)
            if best_tx is not None and best_score >= settings.NAME_SIMILARITY_THRESHOLD:
                status, diff = self._compare_amounts(template.expected_amount, best_tx.amount)
                results.append(self._build_result(template, best_tx, status, diff, f"name_similarity({best_score:.0%})"))
                matched_template_ids.add(template.id)
                matched_transaction_ids.add(best_tx.id)
                unmatched_transactions = [tx for tx in unmatched_transactions if tx.id != best_tx.id]

        # ----- Missing: empleados sin pago bancario -----
        for template in templates:
            if template.id not in matched_template_ids:
                results.append(ReconciliationResultCreate(
                    employee_template_id=template.id,
                    reconciliation_status="missing",
                    expected_amount=template.expected_amount,
                    notes=f"No se encontró transacción en {template.bank_name} para cuenta {template.account_number}",
                    employee_name=template.full_name,
                    bank_name=template.bank_name,
                    account_number=template.account_number,
                ))

        # ----- Extra: transacciones sin empleado en plantilla -----
        for tx in transactions:
            if tx.id not in matched_transaction_ids:
                results.append(ReconciliationResultCreate(
                    bank_transaction_id=tx.id,
                    reconciliation_status="extra",
                    reported_amount=tx.amount,
                    notes=(
                        f"Transacción sin empleado en plantilla "
                        f"(cuenta: {tx.beneficiary_account or 'N/A'})"
                    ),
                    employee_name=tx.beneficiary_name,
                    bank_name=tx.bank_name,
                    account_number=tx.beneficiary_account,
                ))

        # ----- Duplicados: misma cuenta, múltiples transacciones mismo archivo -----
        results = self._flag_duplicates(results, transactions)

        return results

    # ------------------------------------------------------------------
    # Helpers del algoritmo
    # ------------------------------------------------------------------

    def _compare_amounts(self, expected: float, reported: float) -> Tuple[str, float]:
        """Clasifica si hay diferencia de monto dentro de la tolerancia configurada."""
        diff = round(reported - expected, 4)
        if abs(diff) <= settings.AMOUNT_TOLERANCE:
            return "matched", 0.0
        return "difference", diff

    def _build_result(
        self,
        template: EmployeeTemplate,
        tx: BankTransaction,
        status: str,
        diff: float,
        matched_by: str,
    ) -> ReconciliationResultCreate:
        note = None
        if status == "difference":
            sign = "+" if diff > 0 else ""
            note = (
                f"Esperado: {template.expected_amount:,.2f} | "
                f"Reportado: {tx.amount:,.2f} | "
                f"Diferencia: {sign}{diff:,.2f}"
            )
        return ReconciliationResultCreate(
            employee_template_id=template.id,
            bank_transaction_id=tx.id,
            reconciliation_status=status,
            expected_amount=template.expected_amount,
            reported_amount=tx.amount,
            difference_amount=diff if status == "difference" else 0.0,
            notes=note,
            matched_by=matched_by,
            employee_name=template.full_name,
            bank_name=tx.bank_name,
            account_number=template.account_number,
        )

    def _find_template_by_reference(
        self,
        reference: str,
        by_employee_id: Dict[str, EmployeeTemplate],
        bank_name: str,
    ) -> Optional[EmployeeTemplate]:
        """Busca un employee_id embebido en el campo reference."""
        for emp_id, template in by_employee_id.items():
            if emp_id in reference and template.bank_name.lower() == bank_name.lower():
                return template
        return None

    def _find_best_name_match(
        self,
        template: EmployeeTemplate,
        candidates: List[BankTransaction],
    ) -> Tuple[Optional[BankTransaction], float]:
        """
        Retorna la transacción con mayor similitud de nombre para el template dado.
        Solo considera transacciones del mismo banco.
        """
        best_tx: Optional[BankTransaction] = None
        best_score = 0.0
        for tx in candidates:
            if tx.bank_name.lower() != template.bank_name.lower():
                continue
            score = FileProcessor.name_similarity(template.full_name, tx.beneficiary_name)
            if score > best_score:
                best_score = score
                best_tx = tx
        return best_tx, best_score

    def _flag_duplicates(
        self,
        results: List[ReconciliationResultCreate],
        transactions: List[BankTransaction],
    ) -> List[ReconciliationResultCreate]:
        """
        Detecta transacciones duplicadas: misma cuenta + mismo upload_id.
        Cambia su estado a 'duplicate' para que el operador las revise.
        Supuesto: un mismo empleado no debe recibir dos pagos en el mismo archivo.
        """
        # Agrupar IDs de transacción por (upload_id, account)
        account_groups: Dict[Tuple[int, str], List[int]] = defaultdict(list)
        for tx in transactions:
            if tx.beneficiary_account:
                account_groups[(tx.upload_id, tx.beneficiary_account.strip())].append(tx.id)

        duplicate_tx_ids: Set[int] = {
            tx_id
            for tx_ids in account_groups.values()
            if len(tx_ids) > 1
            for tx_id in tx_ids
        }

        if not duplicate_tx_ids:
            return results

        for result in results:
            if result.bank_transaction_id in duplicate_tx_ids:
                result.reconciliation_status = "duplicate"
                result.notes = (
                    f"Duplicado detectado: la cuenta {result.account_number} "
                    f"aparece más de una vez en el mismo archivo bancario. "
                    f"{result.notes or ''}"
                ).strip()

        return results

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _read_file(self, file_path: str) -> pd.DataFrame:
        if file_path.endswith(".xlsx"):
            df = FileProcessor.read_excel(file_path)
        else:
            df = FileProcessor.read_csv(file_path)

        if df.empty:
            raise ValueError("El archivo está vacío o no contiene filas de datos.")
        return df
