"use client";

/**
 * Contexto de autenticación.
 * - Almacena el JWT en localStorage (persistencia) y en una cookie (para el middleware Next.js).
 * - Expone: user, loading, login(), logout()
 */
import {
  createContext, useContext, useEffect, useState, useCallback,
  type ReactNode,
} from "react";
import type { UserProfile } from "./types";

const TOKEN_KEY = "auth_token";
const COOKIE_MAX_AGE = 60 * 60 * 8; // 8 horas en segundos

// ─── Helpers de cookie ──────────────────────────────────────────────────────

function setTokenCookie(token: string) {
  document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Strict`;
}

function clearTokenCookie() {
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; SameSite=Strict`;
}

// ─── Contexto ───────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: UserProfile | null;
  loading: boolean;
  login: (credential: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  /** Carga el perfil del usuario usando el token guardado en localStorage. */
  const loadUser = useCallback(async () => {
    const token = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const res = await fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data: UserProfile = await res.json();
        setUser(data);
      } else {
        // Token inválido o expirado
        localStorage.removeItem(TOKEN_KEY);
        clearTokenCookie();
      }
    } catch {
      // Backend no disponible — mantenemos estado vacío
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUser(); }, [loadUser]);

  const login = useCallback(async (credential: string, password: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? "Error al iniciar sesión");
    }
    const data = await res.json();
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setTokenCookie(data.access_token);
    setUser(data.user);
  }, []);

  const logout = useCallback(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      // Fire-and-forget para registrar el logout en auditoría
      fetch("/api/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {});
    }
    localStorage.removeItem(TOKEN_KEY);
    clearTokenCookie();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}

/** Verifica si el usuario tiene al menos uno de los roles indicados. */
export function hasRole(user: UserProfile | null, ...roles: string[]): boolean {
  if (!user) return false;
  return roles.includes(user.role);
}
