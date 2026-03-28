/**
 * Cliente de API centralizado.
 * Todas las llamadas al backend pasan por aquí.
 * La URL base se lee de NEXT_PUBLIC_API_URL (o localhost:8000 como fallback).
 */
import axios from "axios";
import type {
  Upload,
  ReconciliationSummary,
  BankSummary,
  PaginatedResults,
  ReconciliationResult,
  ReconciliationRunRequest,
  ReconciliationRunResponse,
  ResultFilters,
  UserProfile,
  UserCreate,
  UserUpdate,
  AuditLog,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api`
  : "/api"; // usa el proxy de next.config.js en desarrollo

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
});

// Adjunta el JWT a todas las peticiones
client.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Manejo de errores: extrae detail de FastAPI y redirige en 401
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("auth_token");
      document.cookie = "auth_token=; path=/; max-age=0";
      window.location.href = "/login";
      return Promise.reject(new Error("Sesión expirada."));
    }
    const detail = err.response?.data?.detail;
    const message = detail
      ? typeof detail === "string" ? detail : JSON.stringify(detail)
      : err.message;
    return Promise.reject(new Error(message));
  }
);

// ---------------------------------------------------------------------------
// Uploads
// ---------------------------------------------------------------------------

export async function uploadTemplate(file: File): Promise<Upload> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client.post<{ upload: Upload }>("/uploads/template", form);
  return data.upload;
}

export async function uploadBankReport(file: File, bankName: string): Promise<Upload> {
  const form = new FormData();
  form.append("file", file);
  form.append("bank_name", bankName);
  const { data } = await client.post<{ upload: Upload }>("/uploads/bank-report", form);
  return data.upload;
}

export async function fetchUploads(fileType?: string): Promise<Upload[]> {
  const params = fileType ? { file_type: fileType } : {};
  const { data } = await client.get<Upload[]>("/uploads", { params });
  return data;
}

export async function fetchUpload(id: number): Promise<Upload> {
  const { data } = await client.get<Upload>(`/uploads/${id}`);
  return data;
}

export interface UploadStats {
  total_uploads: number;
  templates_completed: number;
  bank_reports_completed: number;
  banks_available: string[];
  latest_template: { id: number; file_name: string; rows: number } | null;
}

export async function fetchUploadStats(): Promise<UploadStats> {
  const { data } = await client.get<UploadStats>("/uploads/stats/overview");
  return data;
}

// ---------------------------------------------------------------------------
// Reconciliation
// ---------------------------------------------------------------------------

export async function runReconciliation(
  request: ReconciliationRunRequest
): Promise<ReconciliationRunResponse> {
  const { data } = await client.post<ReconciliationRunResponse>("/reconciliation/run", request);
  return data;
}

export async function fetchSummary(): Promise<ReconciliationSummary> {
  const { data } = await client.get<ReconciliationSummary>("/reconciliation/summary");
  return data;
}

export async function fetchBankSummary(): Promise<BankSummary[]> {
  const { data } = await client.get<BankSummary[]>("/reconciliation/bank-summary");
  return data;
}

export async function fetchResults(filters: ResultFilters): Promise<PaginatedResults> {
  const params: Record<string, string | number> = {
    page: filters.page,
    page_size: filters.page_size,
  };
  if (filters.status) params.status = filters.status;
  if (filters.bank_name) params.bank_name = filters.bank_name;
  if (filters.employee_name) params.employee_name = filters.employee_name;
  if (filters.min_amount !== "" && filters.min_amount !== undefined)
    params.min_amount = filters.min_amount;
  if (filters.max_amount !== "" && filters.max_amount !== undefined)
    params.max_amount = filters.max_amount;

  const { data } = await client.get<PaginatedResults>("/reconciliation/results", { params });
  return data;
}

export async function fetchInconsistencies(): Promise<ReconciliationResult[]> {
  const { data } = await client.get<ReconciliationResult[]>("/reconciliation/inconsistencies");
  return data;
}

// ---------------------------------------------------------------------------
// Reports (descarga de archivos)
// ---------------------------------------------------------------------------

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadReport(
  endpoint: string,
  filename: string
): Promise<void> {
  const response = await client.get(endpoint, { responseType: "blob" });
  downloadBlob(response.data, filename);
}

export const REPORT_ENDPOINTS = {
  consolidated: { url: "/reports/consolidated", filename: "conciliacion_completa.csv" },
  inconsistencies: { url: "/reports/inconsistencies", filename: "inconsistencias.csv" },
  missing: { url: "/reports/missing", filename: "faltantes.csv" },
  extras: { url: "/reports/extras", filename: "sobrantes.csv" },
  excel: { url: "/reports/consolidated-excel", filename: "conciliacion_completa.xlsx" },
} as const;

// ---------------------------------------------------------------------------
// Users (admin only)
// ---------------------------------------------------------------------------

export async function fetchUsers(): Promise<UserProfile[]> {
  const { data } = await client.get<UserProfile[]>("/users");
  return data;
}

export async function createUser(payload: UserCreate): Promise<UserProfile> {
  const { data } = await client.post<UserProfile>("/users", payload);
  return data;
}

export async function updateUser(id: number, payload: UserUpdate): Promise<UserProfile> {
  const { data } = await client.put<UserProfile>(`/users/${id}`, payload);
  return data;
}

export async function deactivateUser(id: number): Promise<UserProfile> {
  const { data } = await client.patch<UserProfile>(`/users/${id}/deactivate`);
  return data;
}

export async function activateUser(id: number): Promise<UserProfile> {
  const { data } = await client.patch<UserProfile>(`/users/${id}/activate`);
  return data;
}

export async function fetchAuditLog(): Promise<AuditLog[]> {
  const { data } = await client.get<AuditLog[]>("/audit");
  return data;
}

// ---------------------------------------------------------------------------
// Accounting
// ---------------------------------------------------------------------------
import type {
  ChartOfAccount, JournalEntry, LedgerLine, TrialBalanceLine,
  FiscalPeriod, Budget, BudgetExecutionReport, Invoice, FinancialKPIs,
} from "./types";

export async function fetchAccounts(companyId?: number): Promise<ChartOfAccount[]> {
  const params = companyId ? { company_id: companyId } : {};
  const { data } = await client.get<ChartOfAccount[]>("/accounting/accounts", { params });
  return data;
}

export async function createAccount(payload: {
  code: string; name: string; account_type: string; level?: number; parent_id?: number;
}): Promise<ChartOfAccount> {
  const { data } = await client.post<ChartOfAccount>("/accounting/accounts", payload);
  return data;
}

export async function fetchJournalEntries(params: {
  fiscal_period_id?: number; status?: string; page?: number; page_size?: number;
}): Promise<{ items: JournalEntry[]; total: number; total_pages: number }> {
  const { data } = await client.get("/accounting/entries", { params });
  return data;
}

export async function createJournalEntry(payload: {
  fiscal_period_id: number;
  entry_date: string;
  description: string;
  reference?: string;
  lines: { account_id: number; debit: number; credit: number; description?: string }[];
}): Promise<JournalEntry> {
  const { data } = await client.post<JournalEntry>("/accounting/entries", payload);
  return data;
}

export async function postEntry(entryId: number): Promise<JournalEntry> {
  const { data } = await client.post<JournalEntry>(`/accounting/entries/${entryId}/post`);
  return data;
}

export async function voidEntry(entryId: number, reason: string): Promise<JournalEntry> {
  const { data } = await client.post<JournalEntry>(`/accounting/entries/${entryId}/void`, null, {
    params: { reason },
  });
  return data;
}

export async function fetchLedger(accountId: number, fiscalPeriodId?: number): Promise<{
  account_id: number; account_code: string; account_name: string; lines: LedgerLine[]; final_balance: number;
}> {
  const params = fiscalPeriodId ? { fiscal_period_id: fiscalPeriodId } : {};
  const { data } = await client.get(`/accounting/ledger/${accountId}`, { params });
  return data;
}

export async function fetchTrialBalance(params: {
  fiscal_period_id?: number; company_id?: number;
}): Promise<TrialBalanceLine[]> {
  const { data } = await client.get<TrialBalanceLine[]>("/accounting/trial-balance", { params });
  return data;
}

export async function fetchFiscalPeriods(companyId?: number): Promise<FiscalPeriod[]> {
  const params = companyId ? { company_id: companyId } : {};
  const { data } = await client.get<FiscalPeriod[]>("/accounting/fiscal-periods", { params });
  return data;
}

export async function createFiscalPeriod(payload: {
  year: number; month: number; name: string;
  start_date: string; end_date: string; company_id?: number;
}): Promise<FiscalPeriod> {
  const { data } = await client.post<FiscalPeriod>("/accounting/fiscal-periods", payload);
  return data;
}

// ---------------------------------------------------------------------------
// Budgets
// ---------------------------------------------------------------------------

export async function fetchBudgets(companyId?: number): Promise<Budget[]> {
  const params = companyId ? { company_id: companyId } : {};
  const { data } = await client.get<Budget[]>("/budgets", { params });
  return data;
}

export async function createBudget(payload: {
  fiscal_period_id: number; name: string; cost_center_id?: number;
  lines: { account_id: number; planned_amount: number }[];
}): Promise<Budget> {
  const { data } = await client.post<Budget>("/budgets", payload);
  return data;
}

export async function fetchBudgetExecution(budgetId: number): Promise<BudgetExecutionReport> {
  const { data } = await client.get<BudgetExecutionReport>(`/budgets/${budgetId}/execution`);
  return data;
}

export async function approveBudget(budgetId: number): Promise<Budget> {
  const { data } = await client.post<Budget>(`/budgets/${budgetId}/approve`);
  return data;
}

// ---------------------------------------------------------------------------
// Invoices
// ---------------------------------------------------------------------------

export async function fetchInvoices(params: {
  invoice_type?: string; status?: string; page?: number; page_size?: number;
}): Promise<{ items: Invoice[]; total: number; total_pages: number }> {
  const { data } = await client.get("/invoices", { params });
  return data;
}

export async function createInvoice(payload: {
  invoice_type: string;
  invoice_date: string;
  due_date?: string;
  counterparty_name: string;
  invoice_number?: string;
  lines: { description: string; quantity: number; unit_price: number; tax_rate: number; account_id?: number }[];
}): Promise<Invoice> {
  const { data } = await client.post<Invoice>("/invoices", payload);
  return data;
}

export async function issueInvoice(invoiceId: number): Promise<Invoice> {
  const { data } = await client.post<Invoice>(`/invoices/${invoiceId}/issue`);
  return data;
}

export async function registerPayment(invoiceId: number, payload: {
  payment_date: string; amount: number; payment_method?: string; bank_reference?: string;
}): Promise<{ id: number; amount: number }> {
  const { data } = await client.post(`/invoices/${invoiceId}/payments`, payload);
  return data;
}

export async function downloadInvoicePdf(invoiceId: number): Promise<void> {
  const response = await client.get(`/invoices/${invoiceId}/pdf`, { responseType: "blob" });
  const url = URL.createObjectURL(response.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `factura_${invoiceId}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Financial KPIs Dashboard
// ---------------------------------------------------------------------------

export async function fetchFinancialKPIs(params?: {
  company_id?: number; fiscal_period_id?: number;
}): Promise<FinancialKPIs> {
  const { data } = await client.get<FinancialKPIs>("/dashboard/financial-kpis", { params });
  return data;
}

export async function downloadFinancialReport(
  endpoint: string,
  params: Record<string, string | number>,
  filename: string,
): Promise<void> {
  const response = await client.get(endpoint, { params, responseType: "blob" });
  const url = URL.createObjectURL(response.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
