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
