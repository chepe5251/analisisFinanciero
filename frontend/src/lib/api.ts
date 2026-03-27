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
