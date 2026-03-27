"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from "recharts";
import type { BankSummary } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

interface BankChartProps {
  data: BankSummary[];
}

export function BankChart({ data }: BankChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-gray-400">
        Sin datos de bancos aún
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="bank_name" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(value: number) => formatCurrency(value)}
          contentStyle={{ fontSize: 12, borderRadius: 8 }}
        />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="matched"    name="Conciliado" fill="#10b981" radius={[3,3,0,0]} />
        <Bar dataKey="difference" name="Diferencia" fill="#f59e0b" radius={[3,3,0,0]} />
        <Bar dataKey="missing"    name="Faltante"   fill="#ef4444" radius={[3,3,0,0]} />
        <Bar dataKey="extra"      name="Sobrante"   fill="#f97316" radius={[3,3,0,0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
