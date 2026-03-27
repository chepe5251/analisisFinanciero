"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  History,
  CheckSquare,
  AlertTriangle,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { label: "Dashboard",       href: "/",                icon: LayoutDashboard },
  { label: "Cargar Archivos", href: "/uploads",         icon: Upload          },
  { label: "Historial",       href: "/history",         icon: History         },
  { label: "Conciliación",    href: "/reconciliation",  icon: CheckSquare     },
  { label: "Inconsistencias", href: "/inconsistencies", icon: AlertTriangle   },
  { label: "Reportes",        href: "/reports",         icon: Download        },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-gray-200 bg-white">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-gray-200 px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
          <CheckSquare className="h-4 w-4 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-gray-900">ReconcilaApp</p>
          <p className="text-xs text-gray-500">Conciliación Financiera</p>
        </div>
      </div>

      {/* Navegación */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-1">
          {nav.map(({ label, href, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                  )}
                >
                  <Icon className="h-4 w-4 flex-shrink-0" />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-200 px-5 py-3">
        <p className="text-xs text-gray-400">v1.0.0 — Demo local</p>
      </div>
    </aside>
  );
}
