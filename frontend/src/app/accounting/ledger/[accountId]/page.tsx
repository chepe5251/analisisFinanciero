"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, ArrowLeft } from "lucide-react";
import { fetchLedger } from "@/lib/api";
import type { LedgerLine } from "@/lib/types";
import { Spinner } from "@/components/ui/Spinner";

function fmt(n: number) {
  return n.toLocaleString("es", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function LedgerPage({ params }: { params: { accountId: string } }) {
  const router = useRouter();
  const [data, setData] = useState<{
    account_id: number;
    account_code: string;
    account_name: string;
    lines: LedgerLine[];
    final_balance: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLedger(Number(params.accountId))
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [params.accountId]);

  if (loading) return <div className="flex justify-center py-20"><Spinner /></div>;

  if (error || !data) return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
        {error || "No se encontró la cuenta."}
      </div>
    </div>
  );

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
          <ArrowLeft className="h-4 w-4 text-gray-600" />
        </button>
        <div className="p-2 bg-blue-50 rounded-lg">
          <BookOpen className="h-5 w-5 text-blue-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            Mayor — {data.account_code} {data.account_name}
          </h1>
          <p className="text-sm text-gray-500">Movimientos de la cuenta</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {data.lines.length === 0 ? (
          <div className="py-16 text-center text-gray-400">
            <BookOpen className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>Sin movimientos en esta cuenta.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Asiento</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Fecha</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Descripción</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Referencia</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Débito</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Crédito</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Saldo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.lines.map((line, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-mono text-xs text-gray-500">#{line.entry_id}</td>
                  <td className="px-4 py-2.5 text-gray-600">
                    {new Date(line.entry_date).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2.5 text-gray-800 max-w-xs truncate">{line.description}</td>
                  <td className="px-4 py-2.5 text-gray-500 text-xs">{line.reference || "—"}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-gray-700">
                    {line.debit > 0 ? fmt(line.debit) : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-gray-700">
                    {line.credit > 0 ? fmt(line.credit) : "—"}
                  </td>
                  <td className={`px-4 py-2.5 text-right font-mono font-medium ${line.balance < 0 ? "text-red-600" : "text-gray-800"}`}>
                    {fmt(line.balance)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50 border-t border-gray-200">
              <tr>
                <td colSpan={6} className="px-4 py-2.5 text-sm font-semibold text-gray-700 text-right">
                  SALDO FINAL
                </td>
                <td className={`px-4 py-2.5 text-right font-mono font-bold ${data.final_balance < 0 ? "text-red-600" : "text-gray-900"}`}>
                  {fmt(data.final_balance)}
                </td>
              </tr>
            </tfoot>
          </table>
        )}
      </div>
    </div>
  );
}
