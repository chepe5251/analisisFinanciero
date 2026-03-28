// Tipos que reflejan exactamente los schemas del backend

export type UploadStatus = "pending" | "processing" | "completed" | "failed";
export type FileType = "template" | "bank_report";
export type ReconciliationStatus =
  | "matched"
  | "difference"
  | "missing"
  | "extra"
  | "duplicate"
  | "pending";

export interface Upload {
  id: number;
  file_name: string;
  file_type: FileType;
  source_bank: string | null;
  uploaded_at: string;
  status: UploadStatus;
  total_rows: number;
  processed_rows: number;
  error_rows: number;
  error_message: string | null;
}

export interface ReconciliationResult {
  id: number;
  employee_template_id: number | null;
  bank_transaction_id: number | null;
  reconciliation_status: ReconciliationStatus;
  expected_amount: number | null;
  reported_amount: number | null;
  difference_amount: number | null;
  notes: string | null;
  matched_by: string | null;
  created_at: string;
  employee_name: string | null;
  bank_name: string | null;
  account_number: string | null;
}

export interface ReconciliationSummary {
  total_processed: number;
  total_matched: number;
  total_difference: number;
  total_missing: number;
  total_extra: number;
  total_duplicate: number;
  total_pending: number;
  total_expected_amount: number;
  total_reported_amount: number;
  total_matched_amount: number;
  total_difference_amount: number;
}

export interface BankSummary {
  bank_name: string;
  total_transactions: number;
  total_amount: number;
  matched: number;
  difference: number;
  extra: number;
  missing: number;
  duplicate: number;
}

export interface PaginatedResults {
  items: ReconciliationResult[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ReconciliationRunRequest {
  template_upload_id: number;
  bank_upload_ids: number[];
}

export interface ReconciliationRunResponse {
  summary: ReconciliationSummary;
  message: string;
  batch_id: number | null;
}

// Filtros para la vista de resultados
export interface ResultFilters {
  status?: ReconciliationStatus | "";
  bank_name?: string;
  employee_name?: string;
  min_amount?: number | "";
  max_amount?: number | "";
  page: number;
  page_size: number;
}

// ─── Auth / Usuarios ────────────────────────────────────────────────────────

export type UserRole = "admin" | "operator" | "viewer";

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  role: UserRole;
}

export interface UserUpdate {
  email?: string;
  full_name?: string;
  role?: UserRole;
  password?: string;
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  username: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  detail: string | null;
  ip_address: string | null;
  created_at: string;
}

// ─── Contabilidad ────────────────────────────────────────────────────────────

export type AccountType = "asset" | "liability" | "equity" | "income" | "expense";

export interface ChartOfAccount {
  id: number;
  company_id: number | null;
  code: string;
  name: string;
  account_type: AccountType;
  level: number;
  parent_id: number | null;
  is_active: boolean;
  children?: ChartOfAccount[];
}

export interface JournalEntryLine {
  id: number;
  entry_id: number;
  account_id: number;
  description: string | null;
  debit: number;
  credit: number;
}

export interface JournalEntry {
  id: number;
  fiscal_period_id: number;
  entry_date: string;
  description: string;
  reference: string | null;
  status: "draft" | "posted" | "voided";
  created_at: string;
  lines: JournalEntryLine[];
}

export interface LedgerLine {
  entry_id: number;
  entry_date: string;
  description: string;
  reference: string | null;
  debit: number;
  credit: number;
  balance: number;
}

export interface TrialBalanceLine {
  account_id: number;
  account_code: string;
  account_name: string;
  account_type: AccountType;
  total_debit: number;
  total_credit: number;
  net_balance: number;
}

// ─── Períodos Fiscales ────────────────────────────────────────────────────────

export interface FiscalPeriod {
  id: number;
  year: number;
  month: number;
  name: string;
  start_date: string;
  end_date: string;
  status: "open" | "closed";
}

// ─── Presupuestos ─────────────────────────────────────────────────────────────

export interface BudgetLine {
  id: number;
  account_id: number;
  planned_amount: number;
}

export interface Budget {
  id: number;
  fiscal_period_id: number;
  name: string;
  status: "draft" | "approved" | "closed";
  created_at: string;
  approved_at: string | null;
  lines: BudgetLine[];
}

export interface BudgetExecutionLine {
  account_id: number;
  account_code: string;
  account_name: string;
  planned_amount: number;
  executed_amount: number;
  variance: number;
  execution_pct: number;
}

export interface BudgetExecutionReport {
  budget_id: number;
  budget_name: string;
  fiscal_period: string;
  status: string;
  total_planned: number;
  total_executed: number;
  total_variance: number;
  execution_pct: number;
  lines: BudgetExecutionLine[];
}

// ─── Facturas ─────────────────────────────────────────────────────────────────

export type InvoiceType = "issued" | "received";
export type InvoiceStatus = "draft" | "issued" | "paid" | "overdue" | "voided";

export interface InvoiceLine {
  id: number;
  invoice_id: number;
  description: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  subtotal: number;
  tax_amount: number;
  total: number;
}

export interface Invoice {
  id: number;
  invoice_type: InvoiceType;
  invoice_number: string | null;
  invoice_date: string;
  due_date: string | null;
  counterparty_name: string;
  status: InvoiceStatus;
  subtotal: number;
  tax_amount: number;
  total: number;
  notes: string | null;
  created_at: string;
  lines: InvoiceLine[];
}

export interface AgingBucket {
  bucket: string;
  count: number;
  total_amount: number;
}

// ─── Reportes Financieros ────────────────────────────────────────────────────

export interface FinancialKPIs {
  period_name: string;
  current_ratio: number | null;
  working_capital: number | null;
  net_profit_margin: number | null;
  days_receivable: number | null;
  budget_execution_pct: number | null;
  overdue_invoices_count: number;
  overdue_invoices_amount: number;
  total_revenues: number;
  total_expenses: number;
  net_income: number;
  total_receivables: number;
  total_payables: number;
}
