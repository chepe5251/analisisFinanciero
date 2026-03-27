"use client";

/**
 * AppShell — envuelve el contenido de la app con la barra lateral.
 * En la ruta /login no muestra el sidebar.
 * Mientras se resuelve el estado de auth, muestra un spinner.
 */
import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { useAuth } from "@/lib/auth";
import { Spinner } from "@/components/ui/Spinner";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { loading } = useAuth();

  const isLoginPage = pathname === "/login";

  if (isLoginPage) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center gap-3 text-gray-400">
        <Spinner size="lg" />
        <span className="text-sm">Cargando...</span>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-gray-50">{children}</main>
    </div>
  );
}
