"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { PieChart, ArrowLeft, CheckCircle, TrendingUp, TrendingDown } from "lucide-react";
import { fetchBudgetExecution, approveBudget } from "@/lib/api";
import type { BudgetExecutionReport } from "@/lib/types";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth";

function VarianceBar({ planned, executed }: { planned: number; executed: number }) {
  if (planned === 0) return <span className="text-gray-400 text-xs">—</span>;
  const pct = Math.min((executed / planned) * 100, 150);
  const over = executed > planned;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${over ? "bg-red-400" : "bg-blue-500"}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className={`text-xs font-mono w-12 text-right ${over ? "text-red-600" : "text-gray-600"}`}>
        {((executed / planned) * 100).toFixed(1)}%
      </span>
    </div>
  );
}

function fmt(n: number) {
  return n.toLocaleString("es", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function BudgetDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { user } = useAuth();
  const [report, setReport] = useState<BudgetExecutionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);

  const isAdmin = user?.role === "admin";

  useEffect(() => {
    fetchBudgetExecution(Number(params.id))
      .then(setReport)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [params.id]);

  const handleApprove = async () => {
    if (!report) return;
    setApproving(true);
    try {
      await approveBudget(Number(params.id));
      setReport(prev => prev ? { ...prev, status: "approved" } : prev);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setApproving(false);
    }
  };

  if (loading) return <div className="flex justify-center py-20"><Spinner /></div>;

  if (error || !report) return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
        {error || "No se encontró el presupuesto."}
      </div>
    </div>
  );

  const overBudget = report.total_executed > report.total_planned;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <ArrowLeft className="h-4 w-4 text-gray-600" />
          </button>
          <div className="p-2 bg-purple-50 rounded-lg">
            <PieChart className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">{report.budget_name}</h1>
            <p className="text-sm text-gray-500">{report.fiscal_period} · <span className="capitalize">{report.status}</span></p>
          </div>
        </div>
        {isAdmin && report.status === "draft" && (
          <button
            onClick={handleApprove}
            disabled={approving}
            className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            <CheckCircle className="h-4 w-4" />
            {approving ? "Aprobando..." : "Aprobar Presupuesto"}
          </button>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Planificado", value: fmt(report.total_planned), color: "text-gray-800" },
          { label: "Total Ejecutado", value: fmt(report.total_executed), color: overBudget ? "text-red-600" : "text-blue-600" },
          {
            label: "Varianza",
            value: `${report.total_variance >= 0 ? "+" : ""}${fmt(report.total_variance)}`,
            color: report.total_variance <= 0 ? "text-green-600" : "text-red-600",
          },
          {
            label: "% Ejecución",
            value: `${report.execution_pct.toFixed(1)}%`,
            color: report.execution_pct > 100 ? "text-red-600" : "text-blue-600",
          },
        ].map(kpi => (
          <div key={kpi.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">{kpi.label}</p>
            <p className={`text-lg font-bold font-mono ${kpi.color}`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Execution progress */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-medium text-gray-800">Ejecución Global</h2>
          <div className="flex items-center gap-1 text-sm">
            {overBudget
              ? <><TrendingUp className="h-4 w-4 text-red-500" /><span className="text-red-600">Sobre presupuesto</span></>
              : <><TrendingDown className="h-4 w-4 text-green-500" /><span className="text-green-600">Dentro del presupuesto</span></>
            }
          </div>
        </div>
        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${report.execution_pct > 100 ? "bg-red-500" : report.execution_pct >= 80 ? "bg-green-500" : "bg-blue-500"}`}
            style={{ width: `${Math.min(report.execution_pct, 100)}%` }}
          />
        </div>
        <div className="flex justify-between mt-1 text-xs text-gray-500">
          <span>0%</span>
          <span>{report.execution_pct.toFixed(1)}%</span>
          <span>100%</span>
        </div>
      </div>

      {/* Lines table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100">
          <h2 className="font-medium text-gray-800">Detalle por Cuenta</h2>
        </div>
        {report.lines.length === 0 ? (
          <p className="text-center text-gray-400 text-sm py-8">Sin líneas de presupuesto.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Código</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Cuenta</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Planificado</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Ejecutado</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Varianza</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-44">Ejecución</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {report.lines.map(line => {
                const over = line.executed_amount > line.planned_amount;
                return (
                  <tr key={line.account_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{line.account_code}</td>
                    <td className="px-4 py-2.5 text-gray-800">{line.account_name}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-gray-700">{fmt(line.planned_amount)}</td>
                    <td className={`px-4 py-2.5 text-right font-mono ${over ? "text-red-600" : "text-gray-700"}`}>
                      {fmt(line.executed_amount)}
                    </td>
                    <td className={`px-4 py-2.5 text-right font-mono text-xs ${line.variance <= 0 ? "text-green-600" : "text-red-600"}`}>
                      {line.variance >= 0 ? "+" : ""}{fmt(line.variance)}
                    </td>
                    <td className="px-4 py-2.5">
                      <VarianceBar planned={line.planned_amount} executed={line.executed_amount} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-gray-50 border-t border-gray-200">
              <tr>
                <td colSpan={2} className="px-4 py-2.5 text-sm font-semibold text-gray-700">TOTAL</td>
                <td className="px-4 py-2.5 text-right font-mono font-semibold text-gray-800">{fmt(report.total_planned)}</td>
                <td className={`px-4 py-2.5 text-right font-mono font-semibold ${overBudget ? "text-red-600" : "text-gray-800"}`}>{fmt(report.total_executed)}</td>
                <td className={`px-4 py-2.5 text-right font-mono font-semibold text-sm ${report.total_variance <= 0 ? "text-green-600" : "text-red-600"}`}>
                  {report.total_variance >= 0 ? "+" : ""}{fmt(report.total_variance)}
                </td>
                <td />
              </tr>
            </tfoot>
          </table>
        )}
      </div>
    </div>
  );
}
