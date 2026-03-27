"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Play, RefreshCw, Filter, ChevronLeft, ChevronRight, AlertTriangle } from "lucide-react";
import { fetchUploads, fetchResults, runReconciliation } from "@/lib/api";
import type { Upload, PaginatedResults, ReconciliationStatus } from "@/lib/types";
import { ReconciliationBadge } from "@/components/ui/StatusBadge";
import { Spinner } from "@/components/ui/Spinner";
import { formatCurrency, formatDate } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------
const STATUSES: { value: ReconciliationStatus | ""; label: string }[] = [
  { value: "",           label: "Todos"       },
  { value: "matched",    label: "Conciliado"  },
  { value: "difference", label: "Diferencia"  },
  { value: "missing",    label: "Faltante"    },
  { value: "extra",      label: "Sobrante"    },
  { value: "duplicate",  label: "Duplicado"   },
  { value: "pending",    label: "Pendiente"   },
];

// ---------------------------------------------------------------------------
// Panel de ejecución
// ---------------------------------------------------------------------------
interface RunPanelProps {
  uploads: Upload[];
  onRun: (templateId: number, bankIds: number[]) => void;
  running: boolean;
  runMsg: { type: "ok" | "err"; text: string } | null;
}

function RunPanel({ uploads, onRun, running, runMsg }: RunPanelProps) {
  const templates = uploads.filter(
    (u) => u.file_type === "template" && u.status === "completed"
  );
  const banks = uploads.filter(
    (u) => u.file_type === "bank_report" && u.status === "completed"
  );

  const [templateId, setTemplateId] = useState<number | "">(() =>
    templates.length === 1 ? templates[0].id : ""
  );
  const [bankIds, setBankIds] = useState<number[]>(() =>
    banks.map((b) => b.id)
  );

  // Auto-select cuando los uploads cambian
  useEffect(() => {
    if (templates.length === 1 && templateId === "") {
      setTemplateId(templates[0].id);
    }
  }, [templates, templateId]);

  useEffect(() => {
    if (bankIds.length === 0 && banks.length > 0) {
      setBankIds(banks.map((b) => b.id));
    }
  }, [banks, bankIds.length]);

  function toggleBank(id: number) {
    setBankIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  function handleRun() {
    if (!templateId || bankIds.length === 0) return;
    onRun(Number(templateId), bankIds);
  }

  const canRun = !!templateId && bankIds.length > 0 && !running;

  return (
    <div className="card p-5 space-y-4">
      <h2 className="text-sm font-semibold text-gray-800">Ejecutar conciliación</h2>

      {templates.length === 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          No hay plantillas procesadas.{" "}
          <Link href="/uploads" className="underline font-medium">Sube una plantilla primero.</Link>
        </div>
      )}

      <div className="flex flex-wrap gap-4 items-start">
        {/* Plantilla */}
        <div className="flex-1 min-w-48">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Plantilla de personal
          </label>
          <select
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value ? Number(e.target.value) : "")}
            className="input-base"
            disabled={running}
          >
            <option value="">— Selecciona plantilla —</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                #{t.id} · {t.file_name} ({t.processed_rows} filas)
              </option>
            ))}
          </select>
        </div>

        {/* Bancos */}
        <div className="flex-1 min-w-48">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Reportes bancarios ({bankIds.length} seleccionados)
          </label>
          {banks.length === 0 ? (
            <p className="text-xs text-gray-400 border border-gray-200 rounded-lg p-3">
              Sin reportes bancarios.{" "}
              <Link href="/uploads" className="underline text-blue-600">Subir reportes.</Link>
            </p>
          ) : (
            <div className="border border-gray-200 rounded-lg p-2 space-y-1 max-h-32 overflow-y-auto">
              {banks.map((b) => (
                <label key={b.id} className="flex items-center gap-2 text-xs cursor-pointer hover:bg-gray-50 rounded p-1">
                  <input
                    type="checkbox"
                    checked={bankIds.includes(b.id)}
                    onChange={() => toggleBank(b.id)}
                    disabled={running}
                    className="rounded"
                  />
                  <span className="truncate">
                    <span className="font-medium">{b.source_bank}</span>
                    {" · "}{b.file_name}
                    <span className="text-gray-400"> ({b.processed_rows} tx)</span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Botón */}
        <div className="flex-shrink-0 self-end">
          <button onClick={handleRun} disabled={!canRun} className="btn-primary h-10">
            {running ? <><Spinner size="sm" />Procesando...</> : <><Play className="h-4 w-4" />Ejecutar</>}
          </button>
        </div>
      </div>

      {runMsg && (
        <div className={`rounded-lg border p-3 text-sm ${
          runMsg.type === "ok"
            ? "border-emerald-200 bg-emerald-50 text-emerald-800"
            : "border-red-200 bg-red-50 text-red-800"
        }`}>
          {runMsg.text}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------
export default function ReconciliationPage() {
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [running, setRunning] = useState(false);
  const [runMsg, setRunMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const [results, setResults] = useState<PaginatedResults | null>(null);
  const [loadingResults, setLoadingResults] = useState(false);

  // Filtros
  const [statusFilter, setStatusFilter] = useState<ReconciliationStatus | "">("");
  const [bankFilter, setBankFilter] = useState("");
  const [nameFilter, setNameFilter] = useState("");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 50;

  useEffect(() => {
    fetchUploads().then(setUploads).catch(() => {});
  }, []);

  const loadResults = useCallback(async () => {
    setLoadingResults(true);
    try {
      const data = await fetchResults({
        status: statusFilter || undefined,
        bank_name: bankFilter || undefined,
        employee_name: nameFilter || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setResults(data);
    } catch {
      // silencioso si no hay resultados aún
    } finally {
      setLoadingResults(false);
    }
  }, [statusFilter, bankFilter, nameFilter, page]);

  useEffect(() => { loadResults(); }, [loadResults]);

  async function handleRun(templateId: number, bankIds: number[]) {
    setRunning(true);
    setRunMsg(null);
    try {
      const res = await runReconciliation({
        template_upload_id: templateId,
        bank_upload_ids: bankIds,
      });
      setRunMsg({
        type: "ok",
        text: `${res.message} — ${res.summary.total_processed} registros: `
          + `${res.summary.total_matched} conciliados, `
          + `${res.summary.total_missing} faltantes, `
          + `${res.summary.total_extra} sobrantes.`,
      });
      setPage(1);
      setStatusFilter("");
      loadResults();
    } catch (e: unknown) {
      setRunMsg({
        type: "err",
        text: e instanceof Error ? e.message : "Error al ejecutar conciliación",
      });
    } finally {
      setRunning(false);
    }
  }

  function resetFilters() {
    setStatusFilter("");
    setBankFilter("");
    setNameFilter("");
    setPage(1);
  }

  const hasFilters = statusFilter || bankFilter || nameFilter;

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="page-title">Conciliación</h1>
        <p className="page-subtitle">Ejecuta la conciliación y revisa los resultados</p>
      </div>

      <RunPanel uploads={uploads} onRun={handleRun} running={running} runMsg={runMsg} />

      {/* Filtros */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="h-4 w-4 text-gray-400" />
          <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Filtros</span>
          {hasFilters && (
            <button onClick={resetFilters} className="ml-auto text-xs text-blue-600 underline">
              Limpiar filtros
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-3">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value as ReconciliationStatus | ""); setPage(1); }}
            className="input-base w-auto"
          >
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
          <input
            value={bankFilter}
            onChange={(e) => { setBankFilter(e.target.value); setPage(1); }}
            placeholder="Banco..."
            className="input-base w-36"
          />
          <input
            value={nameFilter}
            onChange={(e) => { setNameFilter(e.target.value); setPage(1); }}
            placeholder="Empleado..."
            className="input-base w-44"
          />
          <button onClick={loadResults} className="btn-secondary" title="Actualizar">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Resultados */}
      {loadingResults ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : results && results.total > 0 ? (
        <div className="card overflow-hidden">
          {/* Header de tabla */}
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between bg-gray-50">
            <span className="text-xs text-gray-500 font-medium">
              {results.total} registros{hasFilters ? " (filtrados)" : ""}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400">
                Página {results.page} de {results.total_pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary py-1 px-2"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(results.total_pages, p + 1))}
                disabled={page >= results.total_pages}
                className="btn-secondary py-1 px-2"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-100">
                <tr>
                  <th className="table-th w-32">Estado</th>
                  <th className="table-th">Empleado</th>
                  <th className="table-th">Banco</th>
                  <th className="table-th">Cuenta</th>
                  <th className="table-th text-right">Esperado</th>
                  <th className="table-th text-right">Reportado</th>
                  <th className="table-th text-right">Diferencia</th>
                  <th className="table-th">Match por</th>
                  <th className="table-th">Notas</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {results.items.map((r) => (
                  <tr key={r.id} className="table-row">
                    <td className="table-td">
                      <ReconciliationBadge status={r.reconciliation_status} />
                    </td>
                    <td className="table-td font-medium text-gray-900 max-w-[180px] truncate">
                      {r.employee_name ?? "—"}
                    </td>
                    <td className="table-td text-gray-500">{r.bank_name ?? "—"}</td>
                    <td className="table-td font-mono text-xs text-gray-500">
                      {r.account_number ?? "—"}
                    </td>
                    <td className="table-td text-right tabular-nums">
                      {formatCurrency(r.expected_amount)}
                    </td>
                    <td className="table-td text-right tabular-nums">
                      {formatCurrency(r.reported_amount)}
                    </td>
                    <td className={`table-td text-right font-semibold tabular-nums ${
                      r.difference_amount && r.difference_amount !== 0
                        ? r.difference_amount > 0 ? "text-amber-600" : "text-red-600"
                        : "text-gray-300"
                    }`}>
                      {r.difference_amount != null && r.difference_amount !== 0
                        ? formatCurrency(r.difference_amount)
                        : "—"}
                    </td>
                    <td className="table-td text-xs text-gray-400 max-w-[100px] truncate">
                      {r.matched_by ?? "—"}
                    </td>
                    <td className="table-td text-xs text-gray-500 max-w-[200px]">
                      <span className="block truncate" title={r.notes ?? ""}>
                        {r.notes ?? "—"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card flex flex-col items-center justify-center py-16 text-gray-400">
          <Play className="h-10 w-10 mb-3 opacity-30" />
          <p className="text-sm font-medium">
            {hasFilters ? "Sin resultados con los filtros actuales" : "Sin resultados de conciliación"}
          </p>
          <p className="text-xs mt-1">
            {hasFilters
              ? "Prueba cambiando los filtros"
              : "Ejecuta la conciliación para ver los resultados aquí"}
          </p>
          {hasFilters && (
            <button onClick={resetFilters} className="mt-3 text-xs text-blue-600 underline">
              Limpiar filtros
            </button>
          )}
        </div>
      )}
    </div>
  );
}
