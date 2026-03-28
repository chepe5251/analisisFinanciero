"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { FileText, Plus, Trash2 } from "lucide-react";
import { createInvoice, fetchAccounts } from "@/lib/api";
import type { ChartOfAccount, InvoiceType } from "@/lib/types";
import { Spinner } from "@/components/ui/Spinner";

interface LineInput {
  description: string;
  quantity: number | "";
  unit_price: number | "";
  tax_rate: number | "";
  account_id: number | "";
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

function calcLine(line: LineInput) {
  const qty = Number(line.quantity) || 0;
  const price = Number(line.unit_price) || 0;
  const tax = Number(line.tax_rate) || 0;
  const subtotal = qty * price;
  const taxAmount = subtotal * (tax / 100);
  return { subtotal, taxAmount, total: subtotal + taxAmount };
}

function fmt(n: number) {
  return n.toLocaleString("es", { minimumFractionDigits: 2 });
}

export default function NewInvoicePage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<ChartOfAccount[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [invoiceType, setInvoiceType] = useState<InvoiceType>("issued");
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().split("T")[0]);
  const [dueDate, setDueDate] = useState("");
  const [counterpartyName, setCounterpartyName] = useState("");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [lines, setLines] = useState<LineInput[]>([
    { description: "", quantity: "", unit_price: "", tax_rate: 0, account_id: "" },
  ]);

  useEffect(() => {
    fetchAccounts()
      .then(data => setAccounts(flattenAccounts(data)))
      .finally(() => setLoadingAccounts(false));
  }, []);

  const updateLine = (idx: number, field: keyof LineInput, value: string) => {
    setLines(prev => {
      const next = [...prev];
      const numFields = ["quantity", "unit_price", "tax_rate"];
      next[idx] = {
        ...next[idx],
        [field]: field === "account_id"
          ? (Number(value) || "")
          : numFields.includes(field)
            ? (value === "" ? "" : Number(value))
            : value,
      };
      return next;
    });
  };

  const addLine = () => setLines(prev => [
    ...prev,
    { description: "", quantity: "", unit_price: "", tax_rate: 0, account_id: "" },
  ]);
  const removeLine = (idx: number) => {
    if (lines.length <= 1) return;
    setLines(prev => prev.filter((_, i) => i !== idx));
  };

  const totals = lines.map(calcLine);
  const grandSubtotal = totals.reduce((s, t) => s + t.subtotal, 0);
  const grandTax = totals.reduce((s, t) => s + t.taxAmount, 0);
  const grandTotal = grandSubtotal + grandTax;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!counterpartyName || !invoiceDate) {
      setError("Completa todos los campos obligatorios.");
      return;
    }
    const validLines = lines.filter(l => l.description && Number(l.quantity) > 0 && Number(l.unit_price) >= 0);
    if (validLines.length === 0) {
      setError("Agrega al menos una línea con descripción y cantidades.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createInvoice({
        invoice_type: invoiceType,
        invoice_date: `${invoiceDate}T00:00:00`,
        due_date: dueDate ? `${dueDate}T00:00:00` : undefined,
        counterparty_name: counterpartyName,
        invoice_number: invoiceNumber || undefined,
        lines: validLines.map(l => ({
          description: l.description,
          quantity: Number(l.quantity),
          unit_price: Number(l.unit_price),
          tax_rate: Number(l.tax_rate) || 0,
          account_id: l.account_id ? Number(l.account_id) : undefined,
        })),
      });
      router.push("/invoices");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loadingAccounts) return <div className="flex justify-center py-20"><Spinner /></div>;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-emerald-50 rounded-lg">
          <FileText className="h-5 w-5 text-emerald-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Nueva Factura</h1>
          <p className="text-sm text-gray-500">Los totales se calculan automáticamente</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Header */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 className="font-medium text-gray-800">Datos de la Factura</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo <span className="text-red-500">*</span>
              </label>
              <select
                value={invoiceType}
                onChange={e => setInvoiceType(e.target.value as InvoiceType)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="issued">Emitida (por cobrar)</option>
                <option value="received">Recibida (por pagar)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Número de Factura
              </label>
              <input
                type="text"
                value={invoiceNumber}
                onChange={e => setInvoiceNumber(e.target.value)}
                placeholder="Ej: F-2024-001"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Contraparte <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={counterpartyName}
              onChange={e => setCounterpartyName(e.target.value)}
              placeholder="Nombre del cliente o proveedor"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fecha <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                value={invoiceDate}
                onChange={e => setInvoiceDate(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Vencimiento</label>
              <input
                type="date"
                value={dueDate}
                onChange={e => setDueDate(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>
        </div>

        {/* Lines */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-medium text-gray-800">Líneas de Factura</h2>
            <button type="button" onClick={addLine} className="text-sm text-emerald-600 hover:underline flex items-center gap-1">
              <Plus className="h-4 w-4" /> Agregar línea
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[720px]">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Descripción</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-600 w-20">Cant.</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-600 w-28">P. Unitario</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-600 w-20">IVA %</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-600 w-28">Subtotal</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-600 w-28">Total</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Cuenta</th>
                  <th className="px-3 py-2 w-10" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {lines.map((line, idx) => {
                  const { subtotal, total } = calcLine(line);
                  return (
                    <tr key={idx}>
                      <td className="px-3 py-2">
                        <input
                          type="text"
                          value={line.description}
                          onChange={e => updateLine(idx, "description", e.target.value)}
                          placeholder="Descripción del producto/servicio"
                          className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          value={line.quantity}
                          onChange={e => updateLine(idx, "quantity", e.target.value)}
                          placeholder="1"
                          min="0"
                          step="0.001"
                          className="w-full border border-gray-300 rounded px-2 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          value={line.unit_price}
                          onChange={e => updateLine(idx, "unit_price", e.target.value)}
                          placeholder="0.00"
                          min="0"
                          step="0.01"
                          className="w-full border border-gray-300 rounded px-2 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          value={line.tax_rate}
                          onChange={e => updateLine(idx, "tax_rate", e.target.value)}
                          placeholder="0"
                          min="0"
                          max="100"
                          step="0.1"
                          className="w-full border border-gray-300 rounded px-2 py-1 text-xs text-right focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        />
                      </td>
                      <td className="px-3 py-2 text-right text-xs font-mono text-gray-600">
                        {fmt(subtotal)}
                      </td>
                      <td className="px-3 py-2 text-right text-xs font-mono font-medium text-gray-800">
                        {fmt(total)}
                      </td>
                      <td className="px-3 py-2">
                        <select
                          value={line.account_id}
                          onChange={e => updateLine(idx, "account_id", e.target.value)}
                          className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        >
                          <option value="">— Cuenta (opcional) —</option>
                          {accounts.map(acc => (
                            <option key={acc.id} value={acc.id}>
                              {acc.code} — {acc.name}
                            </option>
                          ))}
                        </select>
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
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Totals */}
          <div className="border-t border-gray-200 bg-gray-50 px-4 py-3">
            <div className="flex justify-end gap-8 text-sm">
              <div className="text-right space-y-1">
                <div className="flex justify-between gap-12 text-gray-600">
                  <span>Subtotal:</span>
                  <span className="font-mono">{fmt(grandSubtotal)}</span>
                </div>
                <div className="flex justify-between gap-12 text-gray-600">
                  <span>Impuestos:</span>
                  <span className="font-mono">{fmt(grandTax)}</span>
                </div>
                <div className="flex justify-between gap-12 font-bold text-gray-900 border-t border-gray-300 pt-1">
                  <span>TOTAL:</span>
                  <span className="font-mono">{fmt(grandTotal)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={() => router.push("/invoices")}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "Guardando..." : "Guardar Factura"}
          </button>
        </div>
      </form>
    </div>
  );
}
