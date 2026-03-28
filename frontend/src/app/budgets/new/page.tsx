"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PieChart, Plus, Trash2 } from "lucide-react";
import { createBudget, fetchAccounts } from "@/lib/api";
import type { ChartOfAccount } from "@/lib/types";
import { Spinner } from "@/components/ui/Spinner";
import { useEffect } from "react";

interface BudgetLineInput {
  account_id: number | "";
  planned_amount: number | "";
}

function flattenAccounts(accounts: ChartOfAccount[]): ChartOfAccount[] {
  const result: ChartOfAccount[] = [];
  function traverse(items: ChartOfAccount[]) {
    for (const item of items) {
      result.push(item);
      if (item.children) traverse(item.children);
    }
  }
  traverse(accounts);
  return result;
}

export default function NewBudgetPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<ChartOfAccount[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [fiscalPeriodId, setFiscalPeriodId] = useState<number | "">("");
  const [name, setName] = useState("");
  const [lines, setLines] = useState<BudgetLineInput[]>([
    { account_id: "", planned_amount: "" },
  ]);

  useEffect(() => {
    fetchAccounts()
      .then(data => setAccounts(flattenAccounts(data)))
      .finally(() => setLoadingAccounts(false));
  }, []);

  const updateLine = (idx: number, field: keyof BudgetLineInput, value: string) => {
    setLines(prev => {
      const next = [...prev];
      next[idx] = {
        ...next[idx],
        [field]: field === "account_id"
          ? (Number(value) || "")
          : (value === "" ? "" : Number(value)),
      };
      return next;
    });
  };

  const addLine = () => setLines(prev => [...prev, { account_id: "", planned_amount: "" }]);
  const removeLine = (idx: number) => {
    if (lines.length <= 1) return;
    setLines(prev => prev.filter((_, i) => i !== idx));
  };

  const totalPlanned = lines.reduce((s, l) => s + (Number(l.planned_amount) || 0), 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fiscalPeriodId || !name) {
      setError("Completa todos los campos obligatorios.");
      return;
    }
    const validLines = lines.filter(l => l.account_id && Number(l.planned_amount) > 0);
    if (validLines.length === 0) {
      setError("Agrega al menos una línea con cuenta y monto.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createBudget({
        fiscal_period_id: Number(fiscalPeriodId),
        name,
        lines: validLines.map(l => ({
          account_id: Number(l.account_id),
          planned_amount: Number(l.planned_amount),
        })),
      });
      router.push("/budgets");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loadingAccounts) return <div className="flex justify-center py-20"><Spinner /></div>;

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-purple-50 rounded-lg">
          <PieChart className="h-5 w-5 text-purple-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Nuevo Presupuesto</h1>
          <p className="text-sm text-gray-500">Define el presupuesto planificado por cuenta</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 className="font-medium text-gray-800">Datos del Presupuesto</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ID Período Fiscal <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                value={fiscalPeriodId}
                onChange={e => setFiscalPeriodId(e.target.value ? Number(e.target.value) : "")}
                placeholder="Ej: 1"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Ej: Presupuesto Operativo 2024"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
              />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-medium text-gray-800">Líneas Presupuestarias</h2>
            <button type="button" onClick={addLine} className="text-sm text-purple-600 hover:underline flex items-center gap-1">
              <Plus className="h-4 w-4" /> Agregar línea
            </button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Cuenta</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-600 w-40">Monto Planificado</th>
                <th className="px-3 py-2 w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {lines.map((line, idx) => (
                <tr key={idx}>
                  <td className="px-3 py-2">
                    <select
                      value={line.account_id}
                      onChange={e => updateLine(idx, "account_id", e.target.value)}
                      className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500"
                    >
                      <option value="">— Seleccionar cuenta —</option>
                      {accounts.map(acc => (
                        <option key={acc.id} value={acc.id}>
                          {acc.code} — {acc.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      value={line.planned_amount}
                      onChange={e => updateLine(idx, "planned_amount", e.target.value)}
                      placeholder="0.00"
                      min="0"
                      step="0.01"
                      className="w-full border border-gray-300 rounded px-2 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-purple-500"
                    />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button
                      type="button"
                      onClick={() => removeLine(idx)}
                      disabled={lines.length <= 1}
                      className="text-gray-400 hover:text-red-500 disabled:opacity-20"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50 border-t border-gray-200">
              <tr>
                <td className="px-3 py-2 text-sm font-semibold text-gray-700 text-right">TOTAL</td>
                <td className="px-3 py-2 text-right font-mono font-semibold text-gray-800">
                  {totalPlanned.toLocaleString("es", { minimumFractionDigits: 2 })}
                </td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={() => router.push("/budgets")}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "Guardando..." : "Guardar Presupuesto"}
          </button>
        </div>
      </form>
    </div>
  );
}
