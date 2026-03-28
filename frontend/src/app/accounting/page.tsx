"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { BookOpen, Plus, ChevronRight, ChevronDown, BarChart2 } from "lucide-react";
import { fetchAccounts, fetchJournalEntries, postEntry, voidEntry } from "@/lib/api";
import type { ChartOfAccount, JournalEntry } from "@/lib/types";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth";

function AccountNode({ account, depth = 0 }: { account: ChartOfAccount; depth?: number }) {
  const [open, setOpen] = useState(depth < 1);
  const hasChildren = account.children && account.children.length > 0;
  const typeColors: Record<string, string> = {
    asset: "text-blue-600", liability: "text-red-600",
    equity: "text-purple-600", income: "text-green-600", expense: "text-orange-600",
  };
  return (
    <div>
      <div
        className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-gray-50 cursor-pointer"
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
        onClick={() => hasChildren && setOpen(!open)}
      >
        {hasChildren ? (
          open ? <ChevronDown className="h-3.5 w-3.5 text-gray-400" /> : <ChevronRight className="h-3.5 w-3.5 text-gray-400" />
        ) : (
          <span className="w-3.5" />
        )}
        <span className="font-mono text-xs text-gray-500 w-16">{account.code}</span>
        <span className="text-sm text-gray-800 flex-1">{account.name}</span>
        <span className={`text-xs font-medium ${typeColors[account.account_type] || "text-gray-500"}`}>
          {account.account_type}
        </span>
        <Link
          href={`/accounting/ledger/${account.id}`}
          className="text-xs text-blue-600 hover:underline ml-2"
          onClick={e => e.stopPropagation()}
        >
          Mayor
        </Link>
      </div>
      {open && hasChildren && account.children!.map(child => (
        <AccountNode key={child.id} account={child} depth={depth + 1} />
      ))}
    </div>
  );
}

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-yellow-100 text-yellow-700",
  posted: "bg-green-100 text-green-700",
  voided: "bg-gray-100 text-gray-500",
};

export default function AccountingPage() {
  const { user } = useAuth();
  const [accounts, setAccounts] = useState<ChartOfAccount[]>([]);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [loadingEntries, setLoadingEntries] = useState(true);
  const [tab, setTab] = useState<"accounts" | "entries">("accounts");
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAccounts()
      .then(setAccounts)
      .catch(e => setError(e.message))
      .finally(() => setLoadingAccounts(false));
    fetchJournalEntries({ page: 1, page_size: 50 })
      .then(r => setEntries(r.items))
      .catch(e => setError(e.message))
      .finally(() => setLoadingEntries(false));
  }, []);

  const handlePost = async (entryId: number) => {
    setActionLoading(entryId);
    try {
      const updated = await postEntry(entryId);
      setEntries(prev => prev.map(e => e.id === entryId ? updated : e));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleVoid = async (entryId: number) => {
    const reason = prompt("Motivo de anulación:");
    if (!reason) return;
    setActionLoading(entryId);
    try {
      const updated = await voidEntry(entryId, reason);
      setEntries(prev => prev.map(e => e.id === entryId ? updated : e));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const canCreate = user?.role === "admin" || user?.role === "operator";

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-50 rounded-lg">
            <BookOpen className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Contabilidad</h1>
            <p className="text-sm text-gray-500">Plan de cuentas y libro diario</p>
          </div>
        </div>
        {canCreate && (
          <Link
            href="/accounting/entries/new"
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Nuevo Asiento
          </Link>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-6">
          {(["accounts", "entries"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t === "accounts" ? "Plan de Cuentas" : "Libro Diario"}
            </button>
          ))}
        </div>
      </div>

      {/* Plan de cuentas */}
      {tab === "accounts" && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700">{accounts.length} cuentas</p>
            {canCreate && (
              <Link href="/accounting/accounts/new" className="text-sm text-blue-600 hover:underline flex items-center gap-1">
                <Plus className="h-3.5 w-3.5" /> Nueva cuenta
              </Link>
            )}
          </div>
          {loadingAccounts ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : accounts.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <BookOpen className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p>No hay cuentas configuradas.</p>
              {canCreate && <Link href="/accounting/accounts/new" className="text-sm text-blue-600 hover:underline">Crear primera cuenta</Link>}
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {accounts.map(acc => <AccountNode key={acc.id} account={acc} />)}
            </div>
          )}
        </div>
      )}

      {/* Libro Diario */}
      {tab === "entries" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {loadingEntries ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : entries.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <BarChart2 className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p>No hay asientos contables.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">ID</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Fecha</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Descripción</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Referencia</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Estado</th>
                  {canCreate && <th className="px-4 py-3" />}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {entries.map(entry => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-gray-500">#{entry.id}</td>
                    <td className="px-4 py-3 text-gray-700">{new Date(entry.entry_date).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-gray-800 max-w-xs truncate">{entry.description}</td>
                    <td className="px-4 py-3 text-gray-500">{entry.reference || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[entry.status] || "bg-gray-100 text-gray-600"}`}>
                        {entry.status}
                      </span>
                    </td>
                    {canCreate && (
                      <td className="px-4 py-3 text-right">
                        {entry.status === "draft" && (
                          <button
                            onClick={() => handlePost(entry.id)}
                            disabled={actionLoading === entry.id}
                            className="text-xs text-green-600 hover:underline mr-3 disabled:opacity-50"
                          >
                            Publicar
                          </button>
                        )}
                        {entry.status === "posted" && user?.role === "admin" && (
                          <button
                            onClick={() => handleVoid(entry.id)}
                            disabled={actionLoading === entry.id}
                            className="text-xs text-red-600 hover:underline disabled:opacity-50"
                          >
                            Anular
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
