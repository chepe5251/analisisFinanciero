import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  iconColor?: string;
  trend?: "up" | "down" | "neutral";
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  iconColor = "text-blue-600",
  trend,
}: MetricCardProps) {
  return (
    <div className="card p-5 flex items-start gap-4">
      <div className={cn("rounded-lg p-2.5 bg-gray-50", iconColor.replace("text-", "bg-").replace("600", "100"))}>
        <Icon className={cn("h-5 w-5", iconColor)} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide truncate">{title}</p>
        <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
        {subtitle && (
          <p className={cn(
            "mt-0.5 text-xs",
            trend === "up"   ? "text-red-600"     :
            trend === "down" ? "text-emerald-600" : "text-gray-500"
          )}>
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
