"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ShieldCheck, Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Spinner } from "@/components/ui/Spinner";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, user, loading } = useAuth();

  const [credential, setCredential] = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Si ya tiene sesión, redirigir al dashboard
  useEffect(() => {
    if (!loading && user) {
      router.replace(searchParams.get("from") || "/");
    }
  }, [user, loading, router, searchParams]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!credential.trim() || !password) return;
    setError(null);
    setSubmitting(true);
    try {
      await login(credential.trim(), password);
      router.replace(searchParams.get("from") || "/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        {/* Encabezado */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 shadow-lg">
            <ShieldCheck className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">ReconcilaApp</h1>
          <p className="mt-1 text-sm text-gray-500">Conciliación financiera de personal</p>
        </div>

        {/* Formulario */}
        <div className="card p-7 shadow-sm">
          <h2 className="mb-5 text-base font-semibold text-gray-800">Iniciar sesión</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Usuario o correo electrónico
              </label>
              <input
                type="text"
                value={credential}
                onChange={(e) => setCredential(e.target.value)}
                placeholder="admin o admin@reconcilaapp.local"
                className="input-base"
                autoComplete="username"
                required
                disabled={submitting}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Contraseña</label>
              <div className="relative">
                <input
                  type={showPwd ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input-base pr-10"
                  autoComplete="current-password"
                  required
                  disabled={submitting}
                />
                <button
                  type="button"
                  onClick={() => setShowPwd((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  tabIndex={-1}
                >
                  {showPwd ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || !credential.trim() || !password}
              className="btn-primary w-full justify-center"
            >
              {submitting ? <><Spinner size="sm" />Verificando...</> : "Ingresar"}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-gray-400">
          Credenciales por defecto: <span className="font-mono font-medium">admin / Admin1234!</span>
        </p>
      </div>
    </div>
  );
}
