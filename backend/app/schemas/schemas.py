"""
Schemas Pydantic para validación de entrada/salida de la API.
Separados de los modelos SQLAlchemy para no acoplar la capa HTTP al ORM.
"""
from pydantic import BaseModel, field_validator
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
    batch_id: Optional[int] = None          # BUG FIX: asociar al batch para historial
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
    batch_id: Optional[int] = None
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
    status: Optional[str] = None
    bank_name: Optional[str] = None
    employee_name: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    page_size: int = 50


class PaginatedResults(BaseModel):
    items: List[ReconciliationResultOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Summary / Dashboard schemas
# ---------------------------------------------------------------------------

class ReconciliationSummary(BaseModel):
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
    bank_name: str
    total_transactions: int
    total_amount: float
    matched: int = 0
    difference: int = 0
    missing: int = 0
    extra: int = 0
    duplicate: int = 0


class ReconciliationRunRequest(BaseModel):
    template_upload_id: int
    bank_upload_ids: List[int]


class ReconciliationRunResult(BaseModel):
    summary: ReconciliationSummary
    batch_id: int


class ReconciliationRunResponse(BaseModel):
    summary: ReconciliationSummary
    message: str
    batch_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Auth / Usuario schemas
# ---------------------------------------------------------------------------

VALID_ROLES = {"admin", "operator", "viewer"}


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    role: str = "operator"

    @property
    def validated_role(self) -> str:
        if self.role not in VALID_ROLES:
            raise ValueError(f"Rol inválido. Opciones: {', '.join(VALID_ROLES)}")
        return self.role


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    credential: str     # username o email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PermissionInfo(BaseModel):
    resource: str
    action: str
    allowed: bool


# ---------------------------------------------------------------------------
# Auditoría schemas
# ---------------------------------------------------------------------------

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Company schemas
# ---------------------------------------------------------------------------

class CompanyCreate(BaseModel):
    name: str
    tax_id: Optional[str] = None
    address: Optional[str] = None


class CompanyOut(BaseModel):
    id: int
    name: str
    tax_id: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# FiscalPeriod schemas
# ---------------------------------------------------------------------------

class FiscalPeriodCreate(BaseModel):
    company_id: Optional[int] = None
    year: int
    month: int
    name: str
    start_date: datetime
    end_date: datetime


class FiscalPeriodOut(BaseModel):
    id: int
    company_id: Optional[int] = None
    year: int
    month: int
    name: str
    start_date: datetime
    end_date: datetime
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# CostCenter schemas
# ---------------------------------------------------------------------------

class CostCenterCreate(BaseModel):
    company_id: Optional[int] = None
    code: str
    name: str
    description: Optional[str] = None


class CostCenterOut(BaseModel):
    id: int
    company_id: Optional[int] = None
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# ChartOfAccount schemas
# ---------------------------------------------------------------------------

VALID_ACCOUNT_TYPES = {"asset", "liability", "equity", "income", "expense"}


class ChartOfAccountCreate(BaseModel):
    company_id: Optional[int] = None
    code: str
    name: str
    account_type: str
    level: int = 1
    parent_id: Optional[int] = None

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, v: str) -> str:
        if v not in VALID_ACCOUNT_TYPES:
            raise ValueError(f"account_type debe ser uno de: {', '.join(VALID_ACCOUNT_TYPES)}")
        return v


class ChartOfAccountOut(BaseModel):
    id: int
    company_id: Optional[int] = None
    code: str
    name: str
    account_type: str
    level: int
    parent_id: Optional[int] = None
    is_active: bool

    model_config = {"from_attributes": True}


class ChartOfAccountTree(ChartOfAccountOut):
    children: List["ChartOfAccountTree"] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# JournalEntry schemas
# ---------------------------------------------------------------------------

class JournalEntryLineCreate(BaseModel):
    account_id: int
    description: Optional[str] = None
    debit: float = 0.0
    credit: float = 0.0


class JournalEntryLineOut(BaseModel):
    id: int
    entry_id: int
    account_id: int
    description: Optional[str] = None
    debit: float
    credit: float

    model_config = {"from_attributes": True}


class JournalEntryCreate(BaseModel):
    company_id: Optional[int] = None
    fiscal_period_id: int
    cost_center_id: Optional[int] = None
    entry_date: datetime
    description: str
    reference: Optional[str] = None
    lines: List[JournalEntryLineCreate]

    @field_validator("lines")
    @classmethod
    def validate_lines_not_empty(cls, v: List) -> List:
        if not v:
            raise ValueError("El asiento debe tener al menos una línea.")
        return v


class JournalEntryOut(BaseModel):
    id: int
    company_id: Optional[int] = None
    fiscal_period_id: int
    cost_center_id: Optional[int] = None
    entry_date: datetime
    description: str
    reference: Optional[str] = None
    status: str
    created_by_id: Optional[int] = None
    created_at: datetime
    lines: List[JournalEntryLineOut] = []

    model_config = {"from_attributes": True}


class LedgerLine(BaseModel):
    entry_id: int
    entry_date: datetime
    description: str
    reference: Optional[str] = None
    debit: float
    credit: float
    balance: float


class TrialBalanceLine(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    account_type: str
    total_debit: float
    total_credit: float
    net_balance: float


# ---------------------------------------------------------------------------
# Budget schemas
# ---------------------------------------------------------------------------

class BudgetLineCreate(BaseModel):
    account_id: int
    planned_amount: float


class BudgetLineOut(BaseModel):
    id: int
    account_id: int
    planned_amount: float

    model_config = {"from_attributes": True}


class BudgetCreate(BaseModel):
    company_id: Optional[int] = None
    fiscal_period_id: int
    cost_center_id: Optional[int] = None
    name: str
    lines: List[BudgetLineCreate] = []


class BudgetOut(BaseModel):
    id: int
    company_id: Optional[int] = None
    fiscal_period_id: int
    cost_center_id: Optional[int] = None
    name: str
    status: str
    created_at: datetime
    approved_at: Optional[datetime] = None
    lines: List[BudgetLineOut] = []

    model_config = {"from_attributes": True}


class BudgetExecutionLine(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    planned_amount: float
    executed_amount: float
    variance: float
    execution_pct: float


class BudgetExecutionReport(BaseModel):
    budget_id: int
    budget_name: str
    fiscal_period: str
    status: str
    total_planned: float
    total_executed: float
    total_variance: float
    execution_pct: float
    lines: List[BudgetExecutionLine]


# ---------------------------------------------------------------------------
# Invoice schemas
# ---------------------------------------------------------------------------

VALID_INVOICE_TYPES = {"issued", "received"}
VALID_INVOICE_STATUSES = {"draft", "issued", "paid", "overdue", "voided"}


class InvoiceLineCreate(BaseModel):
    account_id: Optional[int] = None
    description: str
    quantity: float = 1.0
    unit_price: float
    tax_rate: float = 0.0


class InvoiceLineOut(BaseModel):
    id: int
    invoice_id: int
    account_id: Optional[int] = None
    description: str
    quantity: float
    unit_price: float
    tax_rate: float
    subtotal: float
    tax_amount: float
    total: float

    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    company_id: Optional[int] = None
    invoice_type: str
    invoice_number: Optional[str] = None
    invoice_date: datetime
    due_date: Optional[datetime] = None
    counterparty_name: str
    counterparty_tax_id: Optional[str] = None
    notes: Optional[str] = None
    lines: List[InvoiceLineCreate]

    @field_validator("invoice_type")
    @classmethod
    def validate_invoice_type(cls, v: str) -> str:
        if v not in VALID_INVOICE_TYPES:
            raise ValueError(f"invoice_type debe ser: {', '.join(VALID_INVOICE_TYPES)}")
        return v


class InvoiceOut(BaseModel):
    id: int
    company_id: Optional[int] = None
    invoice_type: str
    invoice_number: Optional[str] = None
    invoice_date: datetime
    due_date: Optional[datetime] = None
    counterparty_name: str
    counterparty_tax_id: Optional[str] = None
    status: str
    subtotal: float
    tax_amount: float
    total: float
    notes: Optional[str] = None
    created_at: datetime
    lines: List[InvoiceLineOut] = []

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    payment_date: datetime
    amount: float
    payment_method: Optional[str] = None
    bank_reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentOut(BaseModel):
    id: int
    invoice_id: int
    payment_date: datetime
    amount: float
    payment_method: Optional[str] = None
    bank_reference: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgingBucket(BaseModel):
    bucket: str                 # "current" | "1-30" | "31-60" | "61-90" | "90+"
    count: int
    total_amount: float


class AgingReport(BaseModel):
    invoice_type: str           # "issued" (CxC) | "received" (CxP)
    as_of_date: datetime
    buckets: List[AgingBucket]
    total_outstanding: float


# ---------------------------------------------------------------------------
# Financial Reports schemas
# ---------------------------------------------------------------------------

class IncomeStatementLine(BaseModel):
    account_code: str
    account_name: str
    amount: float
    compare_amount: Optional[float] = None


class IncomeStatementSection(BaseModel):
    name: str
    lines: List[IncomeStatementLine]
    total: float
    compare_total: Optional[float] = None


class IncomeStatementReport(BaseModel):
    period_name: str
    compare_period_name: Optional[str] = None
    revenues: IncomeStatementSection
    expenses: IncomeStatementSection
    net_income: float
    compare_net_income: Optional[float] = None


class BalanceSheetSection(BaseModel):
    name: str
    lines: List[IncomeStatementLine]
    total: float


class BalanceSheetReport(BaseModel):
    period_name: str
    assets_current: BalanceSheetSection
    assets_non_current: BalanceSheetSection
    total_assets: float
    liabilities_current: BalanceSheetSection
    liabilities_non_current: BalanceSheetSection
    total_liabilities: float
    equity: BalanceSheetSection
    total_equity: float
    balanced: bool               # total_assets ≈ total_liabilities + total_equity


class CashFlowItem(BaseModel):
    label: str
    amount: float


class CashFlowReport(BaseModel):
    period_name: str
    operating: List[CashFlowItem]
    investing: List[CashFlowItem]
    financing: List[CashFlowItem]
    net_operating: float
    net_investing: float
    net_financing: float
    net_change: float


# ---------------------------------------------------------------------------
# Dashboard KPIs
# ---------------------------------------------------------------------------

class FinancialKPIs(BaseModel):
    period_name: str
    current_ratio: Optional[float] = None           # activo_corriente / pasivo_corriente
    working_capital: Optional[float] = None         # activo_corriente - pasivo_corriente
    net_profit_margin: Optional[float] = None       # utilidad_neta / ingresos * 100
    days_receivable: Optional[float] = None         # CxC / ventas_diarias_promedio
    budget_execution_pct: Optional[float] = None    # % ejecución total del período activo
    overdue_invoices_count: int = 0
    overdue_invoices_amount: float = 0.0
    total_revenues: float = 0.0
    total_expenses: float = 0.0
    net_income: float = 0.0
    total_receivables: float = 0.0
    total_payables: float = 0.0
