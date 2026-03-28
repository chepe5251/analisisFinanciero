"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { FileText, Plus, Download, Filter } from "lucide-react";
import { fetchInvoices, issueInvoice, downloadInvoicePdf } from "@/lib/api";
import type { Invoice, InvoiceType, InvoiceStatus } from "@/lib/types";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth";

const TYPE_LABEL: Record<InvoiceType, string> = {
  issued: "Emitida",
  received: "Recibida",
};

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-yellow-100 text-yellow-700",
  issued: "bg-blue-100 text-blue-700",
  paid: "bg-green-100 text-green-700",
  overdue: "bg-red-100 text-red-700",
  voided: "bg-gray-100 text-gray-500",
};

function fmt(n: number) {
  return n.toLocaleString("es", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function InvoicesPage() {
  const { user } = useAuth();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [total, setTotal] = useState(0);

  const [filterType, setFilterType] = useState<InvoiceType | "">("");
  const [filterStatus, setFilterStatus] = useState<InvoiceStatus | "">("");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  const canCreate = user?.role === "admin" || user?.role === "operator";

  const load = useCallback(() => {
    setLoading(true);
    fetchInvoices({
      invoice_type: filterType || undefined,
      status: filterStatus || undefined,
      page,
      page_size: PAGE_SIZE,
    })
      .then(r => { setInvoices(r.items); setTotal(r.total); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [filterType, filterStatus, page]);

  useEffect(() => { load(); }, [load]);

  const handleIssue = async (id: number) => {
    setActionLoading(id);
    try {
      const updated = await issueInvoice(id);
      setInvoices(prev => prev.map(inv => inv.id === id ? updated : inv));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handlePdf = async (id: number) => {
    setActionLoading(id);
    try {
      await downloadInvoicePdf(id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-50 rounded-lg">
            <FileText className="h-5 w-5 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Facturas</h1>
            <p className="text-sm text-gray-500">Cuentas por cobrar y por pagar</p>
          </div>
        </div>
        {canCreate && (
          <Link
            href="/invoices/new"
            className="flex items-center gap-2 bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Nueva Factura
          </Link>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-xl px-4 py-3">
        <Filter className="h-4 w-4 text-gray-400" />
        <select
          value={filterType}
          onChange={e => { setFilterType(e.target.value as InvoiceType | ""); setPage(1); }}
          className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <option value="">Todos los tipos</option>
          <option value="issued">Emitidas</option>
          <option value="received">Recibidas</option>
        </select>
        <select
          value={filterStatus}
          onChange={e => { setFilterStatus(e.target.value as InvoiceStatus | ""); setPage(1); }}
          className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <option value="">Todos los estados</option>
          <option value="draft">Borrador</option>
          <option value="issued">Emitida</option>
          <option value="paid">Pagada</option>
          <option value="overdue">Vencida</option>
          <option value="voided">Anulada</option>
        </select>
        <span className="ml-auto text-xs text-gray-500">{total} facturas</span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : invoices.length === 0 ? (
          <div className="py-16 text-center text-gray-400">
            <FileText className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>No hay facturas.</p>
            {canCreate && (
              <Link href="/invoices/new" className="text-sm text-emerald-600 hover:underline mt-1 inline-block">
                Crear primera factura
              </Link>
            )}
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Nº</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Tipo</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Fecha</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Vencimiento</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Contraparte</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Total</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Estado</th>
                  {canCreate && <th className="px-4 py-3 w-32" />}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {invoices.map(inv => (
                  <tr key={inv.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">
                      {inv.invoice_number || `#${inv.id}`}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${inv.invoice_type === "issued" ? "bg-blue-50 text-blue-700" : "bg-orange-50 text-orange-700"}`}>
                        {TYPE_LABEL[inv.invoice_type]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {new Date(inv.invoice_date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {inv.due_date ? new Date(inv.due_date).toLocaleDateString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-800 max-w-[180px] truncate">{inv.counterparty_name}</td>
                    <td className="px-4 py-3 text-right font-mono font-medium text-gray-800">
                      {fmt(inv.total)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[inv.status] || "bg-gray-100 text-gray-600"}`}>
                        {inv.status}
                      </span>
                    </td>
                    {canCreate && (
                      <td className="px-4 py-3 text-right space-x-2">
                        {inv.status === "draft" && (
                          <button
                            onClick={() => handleIssue(inv.id)}
                            disabled={actionLoading === inv.id}
                            className="text-xs text-blue-600 hover:underline disabled:opacity-50"
                          >
                            Emitir
                          </button>
                        )}
                        {(inv.status === "issued" || inv.status === "paid") && (
                          <button
                            onClick={() => handlePdf(inv.id)}
                            disabled={actionLoading === inv.id}
                            className="text-xs text-gray-500 hover:text-gray-700 disabled:opacity-50 inline-flex items-center gap-1"
                          >
                            <Download className="h-3 w-3" />PDF
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
                <span className="text-xs text-gray-500">
                  Página {page} de {totalPages}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
                  >
                    Anterior
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-3 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
