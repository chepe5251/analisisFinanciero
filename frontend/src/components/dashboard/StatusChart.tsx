"use client";

import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { ReconciliationSummary } from "@/lib/types";

const COLORS: Record<string, string> = {
  "Conciliado":  "#10b981",
  "Diferencia":  "#f59e0b",
  "Faltante":    "#ef4444",
  "Sobrante":    "#f97316",
  "Duplicado":   "#a855f7",
  "Pendiente":   "#6b7280",
};

interface StatusChartProps {
  summary: ReconciliationSummary;
}

export function StatusChart({ summary }: StatusChartProps) {
  const data = [
    { name: "Conciliado", value: summary.total_matched },
    { name: "Diferencia", value: summary.total_difference },
    { name: "Faltante",   value: summary.total_missing },
    { name: "Sobrante",   value: summary.total_extra },
    { name: "Duplicado",  value: summary.total_duplicate },
    { name: "Pendiente",  value: summary.total_pending },
  ].filter((d) => d.value > 0);

  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-gray-400">
        Sin datos de conciliación aún
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={85}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((entry) => (
            <Cell key={entry.name} fill={COLORS[entry.name] ?? "#6b7280"} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number, name: string) => [value, name]}
          contentStyle={{ fontSize: 12, borderRadius: 8 }}
        />
        <Legend iconType="circle" iconSize={10} wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
