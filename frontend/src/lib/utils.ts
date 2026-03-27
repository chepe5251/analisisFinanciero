import type { ReconciliationStatus, UploadStatus } from "./types";

// ---------------------------------------------------------------------------
// Formateo de moneda y números
// ---------------------------------------------------------------------------

export function formatCurrency(value: number | null | undefined, currency = "USD"): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("es-CR", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("es-CR").format(value);
}

// ---------------------------------------------------------------------------
// Formateo de fechas
// ---------------------------------------------------------------------------

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleString("es-CR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ---------------------------------------------------------------------------
// Labels y colores por estado de conciliación
// ---------------------------------------------------------------------------

export const STATUS_LABEL: Record<ReconciliationStatus, string> = {
  matched:    "Conciliado",
  difference: "Diferencia",
  missing:    "Faltante",
  extra:      "Sobrante",
  duplicate:  "Duplicado",
  pending:    "Pendiente",
};

export const STATUS_COLOR: Record<ReconciliationStatus, string> = {
  matched:    "bg-emerald-100 text-emerald-800",
  difference: "bg-amber-100  text-amber-800",
  missing:    "bg-red-100    text-red-800",
  extra:      "bg-orange-100 text-orange-800",
  duplicate:  "bg-purple-100 text-purple-800",
  pending:    "bg-gray-100   text-gray-700",
};

export const STATUS_DOT: Record<ReconciliationStatus, string> = {
  matched:    "bg-emerald-500",
  difference: "bg-amber-500",
  missing:    "bg-red-500",
  extra:      "bg-orange-500",
  duplicate:  "bg-purple-500",
  pending:    "bg-gray-400",
};

// ---------------------------------------------------------------------------
// Labels y colores por estado de upload
// ---------------------------------------------------------------------------

export const UPLOAD_STATUS_LABEL: Record<UploadStatus, string> = {
  pending:    "Pendiente",
  processing: "Procesando",
  completed:  "Completado",
  failed:     "Fallido",
};

export const UPLOAD_STATUS_COLOR: Record<UploadStatus, string> = {
  pending:    "bg-gray-100   text-gray-700",
  processing: "bg-blue-100   text-blue-800",
  completed:  "bg-emerald-100 text-emerald-800",
  failed:     "bg-red-100    text-red-800",
};

// ---------------------------------------------------------------------------
// Utilidades generales
// ---------------------------------------------------------------------------

export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(" ");
}
