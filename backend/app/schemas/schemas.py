"""
Schemas Pydantic para validación de entrada/salida de la API.
Separados de los modelos SQLAlchemy para no acoplar la capa HTTP al ORM.
"""
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime


# ---------------------------------------------------------------------------
# Upload schemas
# ---------------------------------------------------------------------------

class UploadCreate(BaseModel):
    file_name: str
    file_type: str                        # 'template' | 'bank_report'
    source_bank: Optional[str] = None


class UploadOut(BaseModel):
    id: int
    file_name: str
    file_type: str
    source_bank: Optional[str] = None
    uploaded_at: datetime
    status: str
    total_rows: int
    processed_rows: int
    error_rows: int
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    upload: UploadOut
    message: str


# ---------------------------------------------------------------------------
# Employee Template schemas
# ---------------------------------------------------------------------------

class EmployeeTemplateCreate(BaseModel):
    upload_id: int
    employee_id: str
    full_name: str
    identification: Optional[str] = None
    bank_name: str
    account_number: str
    expected_amount: float
    currency: str = "USD"


class EmployeeTemplateOut(BaseModel):
    id: int
    upload_id: int
    employee_id: str
    full_name: str
    identification: Optional[str] = None
    bank_name: str
    account_number: str
    expected_amount: float
    currency: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Bank Transaction schemas
# ---------------------------------------------------------------------------

class BankTransactionCreate(BaseModel):
    upload_id: int
    bank_name: str
    transaction_date: Optional[datetime] = None
    beneficiary_name: str
    beneficiary_account: Optional[str] = None
    amount: float
    currency: str = "USD"
    reference: Optional[str] = None
    raw_data_json: Optional[Dict[str, Any]] = None


class BankTransactionOut(BaseModel):
    id: int
    upload_id: int
    bank_name: str
    transaction_date: Optional[datetime] = None
    beneficiary_name: str
    beneficiary_account: Optional[str] = None
    amount: float
    currency: str
    reference: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Reconciliation Result schemas
# ---------------------------------------------------------------------------

class ReconciliationResultCreate(BaseModel):
    employee_template_id: Optional[int] = None
    bank_transaction_id: Optional[int] = None
    reconciliation_status: str
    expected_amount: Optional[float] = None
    reported_amount: Optional[float] = None
    difference_amount: Optional[float] = None
    notes: Optional[str] = None
    matched_by: Optional[str] = None
    # Campos desnormalizados
    employee_name: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None


class ReconciliationResultOut(BaseModel):
    id: int
    employee_template_id: Optional[int] = None
    bank_transaction_id: Optional[int] = None
    reconciliation_status: str
    expected_amount: Optional[float] = None
    reported_amount: Optional[float] = None
    difference_amount: Optional[float] = None
    notes: Optional[str] = None
    matched_by: Optional[str] = None
    created_at: datetime
    employee_name: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Filtros para resultados de conciliación
# ---------------------------------------------------------------------------

class ReconciliationFilters(BaseModel):
    """Parámetros de filtrado para la vista de resultados e inconsistencias."""
    status: Optional[str] = None           # matched|difference|missing|extra|duplicate|pending
    bank_name: Optional[str] = None
    employee_name: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    page_size: int = 50


class PaginatedResults(BaseModel):
    """Respuesta paginada genérica."""
    items: List[ReconciliationResultOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Summary / Dashboard schemas
# ---------------------------------------------------------------------------

class ReconciliationSummary(BaseModel):
    """KPIs del dashboard."""
    total_processed: int = 0
    total_matched: int = 0
    total_difference: int = 0
    total_missing: int = 0
    total_extra: int = 0
    total_duplicate: int = 0
    total_pending: int = 0
    total_expected_amount: float = 0.0
    total_reported_amount: float = 0.0
    total_matched_amount: float = 0.0
    total_difference_amount: float = 0.0


class BankSummary(BaseModel):
    """Resumen por banco para el dashboard."""
    bank_name: str
    total_transactions: int
    total_amount: float
    matched: int = 0
    difference: int = 0
    missing: int = 0
    extra: int = 0
    duplicate: int = 0


class ReconciliationRunRequest(BaseModel):
    """Body para POST /reconciliation/run."""
    template_upload_id: int
    bank_upload_ids: List[int]


class ReconciliationRunResult(BaseModel):
    """Resultado interno del servicio de conciliación (no expuesto directamente como HTTP response)."""
    summary: ReconciliationSummary
    batch_id: int


class ReconciliationRunResponse(BaseModel):
    """Respuesta HTTP de POST /reconciliation/run."""
    summary: ReconciliationSummary
    message: str
    batch_id: Optional[int] = None
