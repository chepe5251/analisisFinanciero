"use client";

import { useEffect, useState, useCallback } from "react";
import { RefreshCw, FileText, Building2 } from "lucide-react";
import { fetchUploads } from "@/lib/api";
import type { Upload } from "@/lib/types";
import { UploadBadge } from "@/components/ui/StatusBadge";
import { Spinner } from "@/components/ui/Spinner";
import { formatDate } from "@/lib/utils";

export default function HistoryPage() {
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"" | "template" | "bank_report">("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchUploads(filter || undefined);
      setUploads(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Historial de cargas</h1>
          <p className="page-subtitle">Todos los archivos procesados por el sistema</p>
        </div>
        <button onClick={load} className="btn-secondary">
          <RefreshCw className="h-4 w-4" />
          Actualizar
        </button>
      </div>

      {/* Filtro */}
      <div className="flex gap-2">
        {(["", "template", "bank_report"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-full px-4 py-1.5 text-xs font-medium transition-colors
              ${filter === f ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"}`}
          >
            {f === "" ? "Todos" : f === "template" ? "Plantillas" : "Reportes bancarios"}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : uploads.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-16 text-gray-400">
          <FileText className="h-10 w-10 mb-3 opacity-40" />
          <p className="text-sm">No hay archivos cargados aún</p>
          <p className="text-xs mt-1">Ve a "Cargar Archivos" para comenzar</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="table-th">ID</th>
                <th className="table-th">Archivo</th>
                <th className="table-th">Tipo</th>
                <th className="table-th">Banco</th>
                <th className="table-th">Fecha</th>
                <th className="table-th text-right">Filas</th>
                <th className="table-th text-right">Errores</th>
                <th className="table-th">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {uploads.map((u) => (
                <tr key={u.id} className="table-row">
                  <td className="table-td text-gray-400">#{u.id}</td>
                  <td className="table-td font-medium text-gray-900 flex items-center gap-2">
                    {u.file_type === "template"
                      ? <FileText className="h-4 w-4 text-blue-500 flex-shrink-0" />
                      : <Building2 className="h-4 w-4 text-indigo-500 flex-shrink-0" />}
                    <span className="truncate max-w-xs">{u.file_name}</span>
                  </td>
                  <td className="table-td text-gray-500">
                    {u.file_type === "template" ? "Plantilla" : "Reporte"}
                  </td>
                  <td className="table-td">{u.source_bank ?? "—"}</td>
                  <td className="table-td text-gray-500">{formatDate(u.uploaded_at)}</td>
                  <td className="table-td text-right">{u.processed_rows}</td>
                  <td className="table-td text-right text-red-600">{u.error_rows > 0 ? u.error_rows : "—"}</td>
                  <td className="table-td"><UploadBadge status={u.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
