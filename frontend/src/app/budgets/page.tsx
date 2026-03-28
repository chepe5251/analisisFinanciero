"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { PieChart, Plus, CheckCircle, Clock, XCircle } from "lucide-react";
import { fetchBudgets, approveBudget } from "@/lib/api";
import type { Budget } from "@/lib/types";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth";

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  closed: "bg-gray-100 text-gray-500",
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  draft: <Clock className="h-3.5 w-3.5" />,
  approved: <CheckCircle className="h-3.5 w-3.5" />,
  closed: <XCircle className="h-3.5 w-3.5" />,
};

function ExecutionBar({ pct }: { pct: number }) {
  const clamped = Math.min(Math.max(pct, 0), 100);
  const color = pct > 100 ? "bg-red-500" : pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-blue-500" : "bg-yellow-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${clamped}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-600 w-10 text-right">{pct.toFixed(1)}%</span>
    </div>
  );
}

export default function BudgetsPage() {
  const { user } = useAuth();
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const isAdmin = user?.role === "admin";
  const canCreate = user?.role === "admin" || user?.role === "operator";

  useEffect(() => {
    fetchBudgets()
      .then(setBudgets)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleApprove = async (id: number) => {
    setActionLoading(id);
    try {
      const updated = await approveBudget(id);
      setBudgets(prev => prev.map(b => b.id === id ? updated : b));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-50 rounded-lg">
            <PieChart className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Presupuestos</h1>
            <p className="text-sm text-gray-500">Planificación y control presupuestario</p>
          </div>
        </div>
        {canCreate && (
          <Link
            href="/budgets/new"
            className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Nuevo Presupuesto
          </Link>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : budgets.length === 0 ? (
          <div className="py-16 text-center text-gray-400">
            <PieChart className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>No hay presupuestos creados.</p>
            {canCreate && (
              <Link href="/budgets/new" className="text-sm text-purple-600 hover:underline mt-1 inline-block">
                Crear primer presupuesto
              </Link>
            )}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Nombre</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Período</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Estado</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Líneas</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 w-40">Ejecución</th>
                <th className="px-4 py-3 w-28" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {budgets.map(budget => (
                <tr key={budget.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-gray-500">#{budget.id}</td>
                  <td className="px-4 py-3 font-medium text-gray-800">{budget.name}</td>
                  <td className="px-4 py-3 text-gray-600">Período {budget.fiscal_period_id}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[budget.status] || "bg-gray-100 text-gray-600"}`}>
                      {STATUS_ICON[budget.status]}
                      {budget.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{budget.lines.length} líneas</td>
                  <td className="px-4 py-3 w-40">
                    <ExecutionBar pct={0} />
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <Link
                      href={`/budgets/${budget.id}`}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Detalle
                    </Link>
                    {isAdmin && budget.status === "draft" && (
                      <button
                        onClick={() => handleApprove(budget.id)}
                        disabled={actionLoading === budget.id}
                        className="text-xs text-green-600 hover:underline disabled:opacity-50"
                      >
                        Aprobar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
