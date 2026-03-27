"use client";

import { useState } from "react";
import {
  Download, FileSpreadsheet, FileText, AlertTriangle, XCircle, PlusCircle,
} from "lucide-react";
import { downloadReport, REPORT_ENDPOINTS } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";

interface ReportItem {
  key: keyof typeof REPORT_ENDPOINTS;
  title: string;
  description: string;
  icon: typeof Download;
  iconColor: string;
  format: string;
}

const REPORTS: ReportItem[] = [
  {
    key: "consolidated",
    title: "Reporte consolidado",
    description: "Todos los registros de la conciliación con su estado final.",
    icon: FileText,
    iconColor: "text-blue-600",
    format: "CSV",
  },
  {
    key: "excel",
    title: "Reporte completo (Excel)",
    description: "Archivo Excel con hojas separadas: Resumen, Todos, Inconsistencias, Faltantes y Sobrantes.",
    icon: FileSpreadsheet,
    iconColor: "text-emerald-600",
    format: "XLSX",
  },
  {
    key: "inconsistencies",
    title: "Inconsistencias",
    description: "Registros con diferencias, faltantes, sobrantes o duplicados que requieren revisión.",
    icon: AlertTriangle,
    iconColor: "text-amber-600",
    format: "CSV",
  },
  {
    key: "missing",
    title: "Faltantes",
    description: "Empleados en la plantilla sin transacción bancaria correspondiente.",
    icon: XCircle,
    iconColor: "text-red-600",
    format: "CSV",
  },
  {
    key: "extras",
    title: "Sobrantes",
    description: "Transacciones bancarias sin empleado en la plantilla de personal.",
    icon: PlusCircle,
    iconColor: "text-orange-600",
    format: "CSV",
  },
];

export default function ReportsPage() {
  const [downloading, setDownloading] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function handleDownload(key: keyof typeof REPORT_ENDPOINTS) {
    const { url, filename } = REPORT_ENDPOINTS[key];
    setDownloading(key);
    setErrors((prev) => ({ ...prev, [key]: "" }));
    try {
      await downloadReport(url, filename);
    } catch (e: unknown) {
      setErrors((prev) => ({
        ...prev,
        [key]: e instanceof Error ? e.message : "Error al descargar",
      }));
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <div>
        <h1 className="page-title">Reportes</h1>
        <p className="page-subtitle">
          Descarga los resultados de la conciliación en CSV o Excel.
          Los reportes reflejan la última corrida ejecutada.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {REPORTS.map(({ key, title, description, icon: Icon, iconColor, format }) => (
          <div key={key} className="card p-5 flex flex-col justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className={`rounded-lg p-2 bg-gray-50 flex-shrink-0`}>
                <Icon className={`h-5 w-5 ${iconColor}`} />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{title}</p>
                <p className="text-xs text-gray-500 mt-0.5">{description}</p>
              </div>
            </div>

            {errors[key] && (
              <p className="text-xs text-red-600 -mt-2">{errors[key]}</p>
            )}

            <button
              onClick={() => handleDownload(key as keyof typeof REPORT_ENDPOINTS)}
              disabled={!!downloading}
              className="btn-primary self-start"
            >
              {downloading === key ? (
                <><Spinner size="sm" />Descargando...</>
              ) : (
                <><Download className="h-4 w-4" />Descargar {format}</>
              )}
            </button>
          </div>
        ))}
      </div>

      <div className="rounded-xl bg-blue-50 border border-blue-100 p-4 text-sm text-blue-800">
        <p className="font-semibold mb-1">Nota</p>
        <p className="text-xs text-blue-700">
          Debes ejecutar la conciliación al menos una vez para que los reportes tengan datos.
          Los archivos CSV se abren directamente en Excel o Google Sheets.
        </p>
      </div>
    </div>
  );
}
