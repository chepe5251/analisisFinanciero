"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2, AlertCircle, BookOpen } from "lucide-react";
import { fetchAccounts, createJournalEntry } from "@/lib/api";
import type { ChartOfAccount } from "@/lib/types";
import { Spinner } from "@/components/ui/Spinner";

interface Line {
  account_id: number | "";
  description: string;
  debit: number | "";
  credit: number | "";
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

export default function NewJournalEntryPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<ChartOfAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [fiscalPeriodId, setFiscalPeriodId] = useState<number | "">("");
  const [entryDate, setEntryDate] = useState(new Date().toISOString().split("T")[0]);
  const [description, setDescription] = useState("");
  const [reference, setReference] = useState("");
  const [lines, setLines] = useState<Line[]>([
    { account_id: "", description: "", debit: "", credit: "" },
    { account_id: "", description: "", debit: "", credit: "" },
  ]);

  useEffect(() => {
    fetchAccounts()
      .then(data => setAccounts(flattenAccounts(data)))
      .finally(() => setLoading(false));
  }, []);

  const totalDebit = lines.reduce((s, l) => s + (Number(l.debit) || 0), 0);
  const totalCredit = lines.reduce((s, l) => s + (Number(l.credit) || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01;
  const diff = totalDebit - totalCredit;

  const updateLine = (idx: number, field: keyof Line, value: string) => {
    setLines(prev => {
      const next = [...prev];
      next[idx] = { ...next[idx], [field]: field === "account_id" ? Number(value) || "" : field === "debit" || field === "credit" ? (value === "" ? "" : Number(value)) : value };
      return next;
    });
  };

  const addLine = () => setLines(prev => [...prev, { account_id: "", description: "", debit: "", credit: "" }]);
  const removeLine = (idx: number) => {
    if (lines.length <= 2) return;
    setLines(prev => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fiscalPeriodId || !description || !entryDate) {
      setError("Completa todos los campos obligatorios.");
      return;
    }
    if (!isBalanced) {
      setError(`El asiento no cuadra. Diferencia: ${diff.toFixed(2)}`);
      return;
    }
    const validLines = lines.filter(l => l.account_id && (Number(l.debit) || Number(l.credit)));
    if (validLines.length < 2) {
      setError("El asiento debe tener al menos 2 líneas con cuentas y montos.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createJournalEntry({
        fiscal_period_id: Number(fiscalPeriodId),
        entry_date: `${entryDate}T00:00:00`,
        description,
        reference: reference || undefined,
        lines: validLines.map(l => ({
          account_id: Number(l.account_id),
          debit: Number(l.debit) || 0,
          credit: Number(l.credit) || 0,
          description: l.description || undefined,
        })),
      });
      router.push("/accounting");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex justify-center py-20"><Spinner /></div>;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-50 rounded-lg">
          <BookOpen className="h-5 w-5 text-blue-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Nuevo Asiento Contable</h1>
          <p className="text-sm text-gray-500">El asiento debe cuadrar: Σ Débitos = Σ Créditos</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Encabezado */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 className="font-medium text-gray-800">Datos del Asiento</h2>
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
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fecha <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                value={entryDate}
                onChange={e => setEntryDate(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Descripción <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Ej: Pago de sueldos enero 2024"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Referencia</label>
            <input
              type="text"
              value={reference}
              onChange={e => setReference(e.target.value)}
              placeholder="Número de documento"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Líneas */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-medium text-gray-800">Líneas del Asiento</h2>
            <button type="button" onClick={addLine} className="text-sm text-blue-600 hover:underline flex items-center gap-1">
              <Plus className="h-4 w-4" /> Agregar línea
            </button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Cuenta</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Descripción</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-600 w-32">Débito</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-600 w-32">Crédito</th>
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
                      className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
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
                      type="text"
                      value={line.description}
                      onChange={e => updateLine(idx, "description", e.target.value)}
                      placeholder="Descripción"
                      className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      value={line.debit}
                      onChange={e => updateLine(idx, "debit", e.target.value)}
                      placeholder="0.00"
                      min="0"
                      step="0.01"
                      className="w-full border border-gray-300 rounded px-2 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      value={line.credit}
                      onChange={e => updateLine(idx, "credit", e.target.value)}
                      placeholder="0.00"
                      min="0"
                      step="0.01"
                      className="w-full border border-gray-300 rounded px-2 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button
                      type="button"
                      onClick={() => removeLine(idx)}
                      disabled={lines.length <= 2}
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
                <td colSpan={2} className="px-3 py-2 text-sm font-semibold text-gray-700 text-right">TOTALES</td>
                <td className="px-3 py-2 text-right font-mono font-semibold text-gray-800">{totalDebit.toLocaleString("es", { minimumFractionDigits: 2 })}</td>
                <td className="px-3 py-2 text-right font-mono font-semibold text-gray-800">{totalCredit.toLocaleString("es", { minimumFractionDigits: 2 })}</td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>

        {/* Validación de cuadre */}
        {(totalDebit > 0 || totalCredit > 0) && (
          <div className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm ${
            isBalanced ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
          }`}>
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {isBalanced
              ? `Asiento cuadrado ✓ (${totalDebit.toFixed(2)})`
              : `Diferencia: ${Math.abs(diff).toFixed(2)} — El asiento no cuadra`
            }
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={() => router.push("/accounting")}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={saving || !isBalanced}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "Guardando..." : "Guardar Asiento"}
          </button>
        </div>
      </form>
    </div>
  );
}
