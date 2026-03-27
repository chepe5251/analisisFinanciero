"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  CheckCircle, AlertCircle, XCircle, TrendingUp,
  DollarSign, Users, Building2, RefreshCw,
  Upload, Play, ArrowRight, FileText,
} from "lucide-react";
import {
  fetchSummary, fetchBankSummary, fetchUploads,
  fetchUploadStats, type UploadStats,
} from "@/lib/api";
import type { ReconciliationSummary, BankSummary, Upload as UploadType } from "@/lib/types";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { StatusChart } from "@/components/dashboard/StatusChart";
import { BankChart } from "@/components/dashboard/BankChart";
import { UploadBadge } from "@/components/ui/StatusBadge";
import { Spinner } from "@/components/ui/Spinner";
import { formatCurrency, formatDate } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Estado vacío: guía de primeros pasos
// ---------------------------------------------------------------------------
function GettingStarted({ stats }: { stats: UploadStats }) {
  const hasTemplate = stats.templates_completed > 0;
  const hasBanks = stats.bank_reports_completed > 0;

  const steps = [
    {
      done: hasTemplate,
      num: "1",
      title: "Sube la plantilla de personal",
      desc: "Archivo CSV o Excel con los empleados y montos esperados.",
      href: "/uploads",
      cta: "Ir a Cargar Archivos",
    },
    {
      done: hasBanks,
      num: "2",
      title: "Sube los reportes bancarios",
      desc: hasTemplate
        ? "Agrega los archivos de cada banco que quieras conciliar."
        : "Primero necesitas subir la plantilla.",
      href: "/uploads",
      cta: "Subir reportes",
    },
    {
      done: false,
      num: "3",
      title: "Ejecuta la conciliación",
      desc: hasTemplate && hasBanks
        ? "Todo listo. Puedes ejecutar la conciliación ahora."
        : "Disponible cuando tengas plantilla y al menos un reporte bancario.",
      href: "/reconciliation",
      cta: "Ir a Conciliación",
    },
  ];

  return (
    <div className="card p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="rounded-lg bg-blue-100 p-2">
          <Play className="h-5 w-5 text-blue-600" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-gray-900">Primeros pasos</h2>
          <p className="text-xs text-gray-500">Sigue estos pasos para realizar tu primera conciliación</p>
        </div>
      </div>
      <div className="space-y-3">
        {steps.map((step, i) => (
          <div
            key={i}
            className={`flex items-start gap-4 rounded-lg p-4 border ${
              step.done
                ? "border-emerald-100 bg-emerald-50"
                : i === 0 || steps[i - 1].done
                ? "border-blue-100 bg-blue-50"
                : "border-gray-100 bg-gray-50"
            }`}
          >
            <div className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${
              step.done ? "bg-emerald-500 text-white" : "bg-white border-2 border-gray-300 text-gray-500"
            }`}>
              {step.done ? <CheckCircle className="h-4 w-4" /> : step.num}
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-semibold ${step.done ? "text-emerald-800 line-through opacity-70" : "text-gray-900"}`}>
                {step.title}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">{step.desc}</p>
            </div>
            {!step.done && (steps[i - 1]?.done || i === 0) && (
              <Link href={step.href} className="btn-primary py-1.5 px-3 text-xs flex-shrink-0">
                {step.cta} <ArrowRight className="h-3 w-3" />
              </Link>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------
export default function DashboardPage() {
  const [summary, setSummary] = useState<ReconciliationSummary | null>(null);
  const [bankSummary, setBankSummary] = useState<BankSummary[]>([]);
  const [recentUploads, setRecentUploads] = useState<UploadType[]>([]);
  const [uploadStats, setUploadStats] = useState<UploadStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, b, u, us] = await Promise.all([
        fetchSummary(),
        fetchBankSummary(),
        fetchUploads(),
        fetchUploadStats(),
      ]);
      setSummary(s);
      setBankSummary(b);
      setRecentUploads(u.slice(0, 6));
      setUploadStats(us);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error cargando datos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const hasReconciliationData = summary && summary.total_processed > 0;

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center gap-3 text-gray-400">
        <Spinner size="lg" />
        <span className="text-sm">Cargando dashboard...</span>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">
            {hasReconciliationData
              ? "Resultados de la última conciliación ejecutada"
              : "Sin conciliaciones ejecutadas aún"}
          </p>
        </div>
        <button onClick={load} className="btn-secondary">
          <RefreshCw className="h-4 w-4" />
          Actualizar
        </button>
      </div>

      {/* Error de conexión */}
      {error && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-4 flex items-start gap-3">
          <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800">No se pudo conectar al backend</p>
            <p className="text-xs text-amber-700 mt-0.5">
              {error} — Verifica que el servidor esté corriendo en{" "}
              <code className="bg-amber-100 px-1 rounded">http://localhost:8000</code>
            </p>
          </div>
        </div>
      )}

      {/* Primeros pasos si no hay conciliación */}
      {!hasReconciliationData && !error && uploadStats && (
        <GettingStarted stats={uploadStats} />
      )}

      {/* KPIs de conciliación */}
      {hasReconciliationData && summary && (
        <>
          {/* Fila 1: Conteos */}
          <section>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Registros
            </h2>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <MetricCard
                title="Total procesados"
                value={summary.total_processed}
                icon={Users}
                iconColor="text-blue-600"
              />
              <MetricCard
                title="Conciliados"
                value={summary.total_matched}
                subtitle={`${((summary.total_matched / summary.total_processed) * 100).toFixed(1)}% del total`}
                icon={CheckCircle}
                iconColor="text-emerald-600"
              />
              <MetricCard
                title="Con diferencia"
                value={summary.total_difference}
                icon={AlertCircle}
                iconColor="text-amber-600"
                trend={summary.total_difference > 0 ? "up" : "neutral"}
              />
              <MetricCard
                title="Faltantes + Sobrantes"
                value={summary.total_missing + summary.total_extra}
                subtitle={`${summary.total_missing} faltantes / ${summary.total_extra} sobrantes`}
                icon={XCircle}
                iconColor="text-red-600"
                trend={summary.total_missing + summary.total_extra > 0 ? "up" : "neutral"}
              />
            </div>
          </section>

          {/* Fila 2: Montos */}
          <section>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Montos
            </h2>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <MetricCard
                title="Esperado total"
                value={formatCurrency(summary.total_expected_amount)}
                icon={DollarSign}
                iconColor="text-blue-600"
              />
              <MetricCard
                title="Reportado total"
                value={formatCurrency(summary.total_reported_amount)}
                icon={DollarSign}
                iconColor="text-indigo-600"
              />
              <MetricCard
                title="Monto conciliado"
                value={formatCurrency(summary.total_matched_amount)}
                icon={CheckCircle}
                iconColor="text-emerald-600"
              />
              <MetricCard
                title="En diferencias"
                value={formatCurrency(summary.total_difference_amount)}
                icon={TrendingUp}
                iconColor="text-amber-600"
                trend={summary.total_difference_amount > 0 ? "up" : "neutral"}
              />
            </div>
          </section>

          {/* Link a inconsistencias si las hay */}
          {(summary.total_difference + summary.total_missing + summary.total_extra + summary.total_duplicate) > 0 && (
            <div className="rounded-lg bg-amber-50 border border-amber-200 p-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-amber-600" />
                <span className="text-sm text-amber-800 font-medium">
                  Hay{" "}
                  {summary.total_difference + summary.total_missing + summary.total_extra + summary.total_duplicate}{" "}
                  registros que requieren revisión
                </span>
              </div>
              <Link href="/inconsistencies" className="btn-primary py-1.5 px-3 text-xs">
                Revisar inconsistencias <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          )}

          {/* Gráficas */}
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-1">
                Distribución por estado
              </h3>
              <p className="text-xs text-gray-400 mb-4">¿Cómo están clasificados los registros?</p>
              <StatusChart summary={summary} />
            </div>

            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-1">
                Transacciones por banco
              </h3>
              <p className="text-xs text-gray-400 mb-4">Estado de cada banco en la conciliación</p>
              <BankChart data={bankSummary} />
            </div>
          </div>

          {/* Resumen por banco */}
          {bankSummary.length > 0 && (
            <div className="card overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
                <Building2 className="h-4 w-4 text-gray-400" />
                <h3 className="text-sm font-semibold text-gray-700">Detalle por banco</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr>
                      <th className="table-th">Banco</th>
                      <th className="table-th text-right">Total</th>
                      <th className="table-th text-right">Monto</th>
                      <th className="table-th text-right text-emerald-700">Conciliados</th>
                      <th className="table-th text-right text-amber-700">Diferencias</th>
                      <th className="table-th text-right text-red-700">Faltantes</th>
                      <th className="table-th text-right text-orange-700">Sobrantes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {bankSummary.map((b) => (
                      <tr key={b.bank_name} className="table-row">
                        <td className="table-td font-semibold text-gray-900">{b.bank_name}</td>
                        <td className="table-td text-right text-gray-500">{b.total_transactions}</td>
                        <td className="table-td text-right font-medium">{formatCurrency(b.total_amount)}</td>
                        <td className="table-td text-right text-emerald-700 font-medium">{b.matched}</td>
                        <td className="table-td text-right text-amber-700 font-medium">{b.difference}</td>
                        <td className="table-td text-right text-red-700 font-medium">{b.missing ?? 0}</td>
                        <td className="table-td text-right text-orange-700 font-medium">{b.extra}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Últimas cargas — siempre visible */}
      {recentUploads.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-gray-400" />
              <h3 className="text-sm font-semibold text-gray-700">Archivos recientes</h3>
            </div>
            <Link href="/history" className="text-xs text-blue-600 hover:underline">
              Ver todos →
            </Link>
          </div>
          <ul className="divide-y divide-gray-50">
            {recentUploads.map((u) => (
              <li key={u.id} className="flex items-center justify-between px-5 py-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{u.file_name}</p>
                  <p className="text-xs text-gray-400">
                    {u.file_type === "template" ? "Plantilla" : `Banco: ${u.source_bank}`}
                    {" · "}{formatDate(u.uploaded_at)}
                  </p>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-4">
                  {u.processed_rows > 0 && (
                    <span className="text-xs text-gray-400">{u.processed_rows} filas</span>
                  )}
                  <UploadBadge status={u.status} />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
