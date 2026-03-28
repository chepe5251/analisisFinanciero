"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard, Upload, History, CheckSquare,
  AlertTriangle, Download, Users, LogOut, ShieldCheck,
  BookOpen, PieChart, FileText, BarChart3,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth, hasRole } from "@/lib/auth";
import type { UserRole } from "@/lib/types";

interface NavItem {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  roles: UserRole[];   // roles que pueden ver este ítem
}

const NAV: NavItem[] = [
  // Inicio
  { label: "Dashboard",        href: "/",                icon: LayoutDashboard, roles: ["admin", "operator", "viewer"] },
  // Conciliación
  { label: "Cargar Archivos",  href: "/uploads",         icon: Upload,          roles: ["admin", "operator"] },
  { label: "Historial",        href: "/history",         icon: History,         roles: ["admin", "operator", "viewer"] },
  { label: "Conciliación",     href: "/reconciliation",  icon: CheckSquare,     roles: ["admin", "operator"] },
  { label: "Inconsistencias",  href: "/inconsistencies", icon: AlertTriangle,   roles: ["admin", "operator", "viewer"] },
  // Contabilidad y finanzas
  { label: "Contabilidad",     href: "/accounting",      icon: BookOpen,        roles: ["admin", "operator", "viewer"] },
  { label: "Presupuestos",     href: "/budgets",         icon: PieChart,        roles: ["admin", "operator", "viewer"] },
  { label: "Facturas",         href: "/invoices",        icon: FileText,        roles: ["admin", "operator", "viewer"] },
  { label: "Reportes",         href: "/reports",         icon: BarChart3,       roles: ["admin", "operator", "viewer"] },
  // Admin
  { label: "Usuarios",         href: "/users",           icon: Users,           roles: ["admin"] },
];

const ROLE_LABEL: Record<UserRole, string> = {
  admin:    "Administrador",
  operator: "Operador",
  viewer:   "Auditor",
};

const ROLE_COLOR: Record<UserRole, string> = {
  admin:    "bg-purple-100 text-purple-700",
  operator: "bg-blue-100 text-blue-700",
  viewer:   "bg-gray-100 text-gray-600",
};

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  const visibleNav = NAV.filter((item) =>
    user ? hasRole(user, ...item.roles) : false
  );

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-gray-200 bg-white">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-gray-200 px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
          <ShieldCheck className="h-4 w-4 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-gray-900">ReconcilaApp</p>
          <p className="text-xs text-gray-500">Conciliación Financiera</p>
        </div>
      </div>

      {/* Navegación */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-1">
          {visibleNav.map(({ label, href, icon: Icon }) => {
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

      {/* Usuario + logout */}
      {user && (
        <div className="border-t border-gray-200 px-4 py-3 space-y-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-gray-200 text-xs font-bold text-gray-600 uppercase">
              {user.username[0]}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-gray-800 truncate">{user.full_name || user.username}</p>
              <p className="text-xs text-gray-400 truncate">{user.email}</p>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full", ROLE_COLOR[user.role])}>
              {ROLE_LABEL[user.role]}
            </span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-600 transition-colors"
              title="Cerrar sesión"
            >
              <LogOut className="h-3.5 w-3.5" />
              Salir
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
