"use client";

import { useEffect, useState, useCallback } from "react";
import { AlertTriangle, RefreshCw, Filter } from "lucide-react";
import { fetchInconsistencies } from "@/lib/api";
import type { ReconciliationResult, ReconciliationStatus } from "@/lib/types";
import { ReconciliationBadge } from "@/components/ui/StatusBadge";
import { Spinner } from "@/components/ui/Spinner";
import { formatCurrency, STATUS_LABEL } from "@/lib/utils";

const STATUS_GROUPS: ReconciliationStatus[] = ["difference", "missing", "extra", "duplicate", "pending"];

export default function InconsistenciesPage() {
  const [all, setAll] = useState<ReconciliationResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<ReconciliationStatus | "">("");
  const [bankFilter, setBankFilter] = useState("");
  const [nameFilter, setNameFilter] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInconsistencies();
      setAll(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = all.filter((r) => {
    if (statusFilter && r.reconciliation_status !== statusFilter) return false;
    if (bankFilter && !r.bank_name?.toLowerCase().includes(bankFilter.toLowerCase())) return false;
    if (nameFilter && !r.employee_name?.toLowerCase().includes(nameFilter.toLowerCase())) return false;
    return true;
  });

  // Conteo por estado para los tabs rápidos
  const counts = STATUS_GROUPS.reduce((acc, s) => {
    acc[s] = all.filter((r) => r.reconciliation_status === s).length;
    return acc;
  }, {} as Record<ReconciliationStatus, number>);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <AlertTriangle className="h-6 w-6 text-amber-500" />
            Inconsistencias
          </h1>
          <p className="page-subtitle">Registros que requieren revisión del operador</p>
        </div>
        <button onClick={load} className="btn-secondary">
          <RefreshCw className="h-4 w-4" />
          Actualizar
        </button>
      </div>

      {/* Tabs de estado rápido */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setStatusFilter("")}
          className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors
            ${statusFilter === "" ? "bg-gray-800 text-white" : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"}`}
        >
          Todos ({all.length})
        </button>
        {STATUS_GROUPS.map((s) => counts[s] > 0 && (
          <button
            key={s}
            onClick={() => setStatusFilter(s === statusFilter ? "" : s)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors
              ${statusFilter === s ? "bg-gray-800 text-white" : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"}`}
          >
            {STATUS_LABEL[s]} ({counts[s]})
          </button>
        ))}
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3 items-center text-sm text-gray-500">
        <Filter className="h-4 w-4" />
        <input value={bankFilter} onChange={(e) => setBankFilter(e.target.value)} placeholder="Banco..." className="input-base w-40" />
        <input value={nameFilter} onChange={(e) => setNameFilter(e.target.value)} placeholder="Empleado..." className="input-base w-48" />
        {(bankFilter || nameFilter) && (
          <button onClick={() => { setBankFilter(""); setNameFilter(""); }} className="text-xs text-gray-400 underline">
            Limpiar
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : filtered.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-16 text-gray-400">
          <AlertTriangle className="h-10 w-10 mb-3 opacity-30" />
          <p className="text-sm">
            {all.length === 0 ? "No hay resultados de conciliación aún" : "No hay inconsistencias con los filtros actuales"}
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <span className="text-sm text-gray-500">{filtered.length} registros</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="table-th">Estado</th>
                  <th className="table-th">Empleado</th>
                  <th className="table-th">Banco</th>
                  <th className="table-th">Cuenta</th>
                  <th className="table-th text-right">Esperado</th>
                  <th className="table-th text-right">Reportado</th>
                  <th className="table-th text-right">Diferencia</th>
                  <th className="table-th">Detalle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((r) => (
                  <tr key={r.id} className="table-row">
                    <td className="table-td"><ReconciliationBadge status={r.reconciliation_status} /></td>
                    <td className="table-td font-medium text-gray-900">{r.employee_name ?? "—"}</td>
                    <td className="table-td text-gray-500">{r.bank_name ?? "—"}</td>
                    <td className="table-td text-gray-500 font-mono text-xs">{r.account_number ?? "—"}</td>
                    <td className="table-td text-right">{formatCurrency(r.expected_amount)}</td>
                    <td className="table-td text-right">{formatCurrency(r.reported_amount)}</td>
                    <td className={`table-td text-right font-semibold ${r.difference_amount && r.difference_amount !== 0 ? "text-red-600" : "text-gray-300"}`}>
                      {r.difference_amount != null && r.difference_amount !== 0 ? formatCurrency(r.difference_amount) : "—"}
                    </td>
                    <td className="table-td text-xs text-gray-500 max-w-xs">
                      <span className="block truncate" title={r.notes ?? ""}>{r.notes ?? "—"}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
