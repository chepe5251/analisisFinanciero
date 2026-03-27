"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Users, Plus, RefreshCw, Shield, Eye, Wrench,
  CheckCircle, XCircle, X, AlertCircle,
} from "lucide-react";
import {
  fetchUsers, createUser, updateUser,
  deactivateUser, activateUser, fetchAuditLog,
} from "@/lib/api";
import type { UserProfile, UserCreate, UserUpdate, UserRole, AuditLog } from "@/lib/types";
import { useAuth, hasRole } from "@/lib/auth";
import { Spinner } from "@/components/ui/Spinner";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";

// ─── Badges ─────────────────────────────────────────────────────────────────

const ROLE_BADGE: Record<UserRole, string> = {
  admin:    "bg-purple-100 text-purple-700 border-purple-200",
  operator: "bg-blue-100 text-blue-700 border-blue-200",
  viewer:   "bg-gray-100 text-gray-600 border-gray-200",
};
const ROLE_LABEL: Record<UserRole, string> = {
  admin: "Administrador", operator: "Operador", viewer: "Auditor",
};
const ROLE_ICON: Record<UserRole, typeof Shield> = {
  admin: Shield, operator: Wrench, viewer: Eye,
};

// ─── Modal de crear/editar usuario ──────────────────────────────────────────

interface UserModalProps {
  editing: UserProfile | null;
  onClose: () => void;
  onSaved: () => void;
}

function UserModal({ editing, onClose, onSaved }: UserModalProps) {
  const isEdit = !!editing;
  const [form, setForm] = useState({
    username: editing?.username ?? "",
    email: editing?.email ?? "",
    full_name: editing?.full_name ?? "",
    role: (editing?.role ?? "operator") as UserRole,
    password: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set<K extends keyof typeof form>(k: K, v: typeof form[K]) {
    setForm((p) => ({ ...p, [k]: v }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (isEdit) {
        const payload: UserUpdate = {
          email: form.email || undefined,
          full_name: form.full_name || undefined,
          role: form.role,
          password: form.password || undefined,
        };
        await updateUser(editing!.id, payload);
      } else {
        const payload: UserCreate = {
          username: form.username,
          email: form.email,
          full_name: form.full_name || undefined,
          role: form.role,
          password: form.password,
        };
        await createUser(payload);
      }
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error guardando usuario");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-gray-900">
            {isEdit ? "Editar usuario" : "Crear usuario"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isEdit && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Username *</label>
              <input
                value={form.username}
                onChange={(e) => set("username", e.target.value)}
                placeholder="jperez"
                className="input-base"
                required
                disabled={saving}
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Correo electrónico *</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
              placeholder="jperez@empresa.com"
              className="input-base"
              required
              disabled={saving}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Nombre completo</label>
            <input
              value={form.full_name}
              onChange={(e) => set("full_name", e.target.value)}
              placeholder="Juan Pérez"
              className="input-base"
              disabled={saving}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Rol *</label>
            <select
              value={form.role}
              onChange={(e) => set("role", e.target.value as UserRole)}
              className="input-base"
              disabled={saving}
            >
              <option value="viewer">Auditor — solo lectura</option>
              <option value="operator">Operador — carga y conciliación</option>
              <option value="admin">Administrador — acceso total</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              {isEdit ? "Nueva contraseña (dejar vacío para no cambiar)" : "Contraseña *"}
            </label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => set("password", e.target.value)}
              placeholder="Mín. 8 caracteres"
              className="input-base"
              required={!isEdit}
              disabled={saving}
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center" disabled={saving}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary flex-1 justify-center" disabled={saving}>
              {saving ? <><Spinner size="sm" />Guardando...</> : (isEdit ? "Guardar cambios" : "Crear usuario")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Página principal ────────────────────────────────────────────────────────

type Tab = "users" | "audit";

export default function UsersPage() {
  const router = useRouter();
  const { user: currentUser, loading: authLoading } = useAuth();

  const [tab, setTab] = useState<Tab>("users");
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<"create" | UserProfile | null>(null);
  const [toggling, setToggling] = useState<number | null>(null);

  // Guard: solo admin
  useEffect(() => {
    if (!authLoading && currentUser && !hasRole(currentUser, "admin")) {
      router.replace("/");
    }
  }, [currentUser, authLoading, router]);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [u, a] = await Promise.all([fetchUsers(), fetchAuditLog()]);
      setUsers(u);
      setAuditLogs(a);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error cargando datos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (!authLoading && currentUser) loadUsers(); }, [loadUsers, authLoading, currentUser]);

  async function handleToggleActive(u: UserProfile) {
    setToggling(u.id);
    try {
      const updated = u.is_active ? await deactivateUser(u.id) : await activateUser(u.id);
      setUsers((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error actualizando usuario");
    } finally {
      setToggling(null);
    }
  }

  if (authLoading || (!currentUser && !authLoading)) {
    return <div className="flex h-full items-center justify-center"><Spinner size="lg" /></div>;
  }

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Users className="h-6 w-6 text-gray-700" />
            Gestión de usuarios
          </h1>
          <p className="page-subtitle">Administra cuentas y revisa el log de auditoría</p>
        </div>
        <div className="flex gap-2">
          <button onClick={loadUsers} className="btn-secondary">
            <RefreshCw className="h-4 w-4" /> Actualizar
          </button>
          {tab === "users" && (
            <button onClick={() => setModal("create")} className="btn-primary">
              <Plus className="h-4 w-4" /> Nuevo usuario
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {(["users", "audit"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px",
              tab === t
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            )}
          >
            {t === "users" ? `Usuarios (${users.length})` : `Auditoría (${auditLogs.length})`}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 flex-shrink-0" /> {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : tab === "users" ? (
        /* ── Tabla de usuarios ── */
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="table-th">Usuario</th>
                <th className="table-th">Correo</th>
                <th className="table-th">Rol</th>
                <th className="table-th">Estado</th>
                <th className="table-th">Último acceso</th>
                <th className="table-th">Creado</th>
                <th className="table-th text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u) => {
                const RoleIcon = ROLE_ICON[u.role];
                return (
                  <tr key={u.id} className={cn("table-row", !u.is_active && "opacity-60")}>
                    <td className="table-td">
                      <div className="flex items-center gap-2">
                        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-600 uppercase">
                          {u.username[0]}
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{u.username}</p>
                          {u.full_name && <p className="text-xs text-gray-400">{u.full_name}</p>}
                        </div>
                      </div>
                    </td>
                    <td className="table-td text-gray-500">{u.email}</td>
                    <td className="table-td">
                      <span className={cn("flex items-center gap-1 w-fit border rounded-full px-2 py-0.5 text-xs font-medium", ROLE_BADGE[u.role])}>
                        <RoleIcon className="h-3 w-3" />
                        {ROLE_LABEL[u.role]}
                      </span>
                    </td>
                    <td className="table-td">
                      {u.is_active
                        ? <span className="flex items-center gap-1 text-emerald-600 text-xs font-medium"><CheckCircle className="h-3.5 w-3.5" />Activo</span>
                        : <span className="flex items-center gap-1 text-red-500 text-xs font-medium"><XCircle className="h-3.5 w-3.5" />Inactivo</span>
                      }
                    </td>
                    <td className="table-td text-gray-400 text-xs">
                      {u.last_login_at ? formatDate(u.last_login_at) : "—"}
                    </td>
                    <td className="table-td text-gray-400 text-xs">
                      {formatDate(u.created_at)}
                    </td>
                    <td className="table-td text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setModal(u)}
                          className="btn-secondary py-1 px-2 text-xs"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => handleToggleActive(u)}
                          disabled={toggling === u.id || u.id === currentUser?.id}
                          className={cn(
                            "py-1 px-2 text-xs rounded-lg border font-medium transition-colors",
                            u.is_active
                              ? "border-red-200 text-red-600 hover:bg-red-50"
                              : "border-emerald-200 text-emerald-700 hover:bg-emerald-50",
                            (toggling === u.id || u.id === currentUser?.id) && "opacity-50 cursor-not-allowed"
                          )}
                        >
                          {toggling === u.id
                            ? <Spinner size="sm" />
                            : u.is_active ? "Desactivar" : "Activar"
                          }
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {users.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <Users className="h-10 w-10 mb-2 opacity-30" />
              <p className="text-sm">No hay usuarios registrados</p>
            </div>
          )}
        </div>
      ) : (
        /* ── Log de auditoría ── */
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="table-th">Fecha</th>
                  <th className="table-th">Usuario</th>
                  <th className="table-th">Acción</th>
                  <th className="table-th">Recurso</th>
                  <th className="table-th">Detalle</th>
                  <th className="table-th">IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {auditLogs.map((log) => (
                  <tr key={log.id} className="table-row">
                    <td className="table-td text-xs text-gray-400 whitespace-nowrap">
                      {formatDate(log.created_at)}
                    </td>
                    <td className="table-td font-medium text-gray-700">{log.username ?? "—"}</td>
                    <td className="table-td">
                      <span className="font-mono text-xs text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">
                        {log.action}
                      </span>
                    </td>
                    <td className="table-td text-xs text-gray-500">
                      {log.resource_type ? `${log.resource_type}${log.resource_id ? ` #${log.resource_id}` : ""}` : "—"}
                    </td>
                    <td className="table-td text-xs text-gray-500 max-w-xs">
                      <span className="block truncate" title={log.detail ?? ""}>{log.detail ?? "—"}</span>
                    </td>
                    <td className="table-td text-xs font-mono text-gray-400">{log.ip_address ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {auditLogs.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                <p className="text-sm">Sin eventos registrados aún</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal crear/editar */}
      {modal !== null && (
        <UserModal
          editing={modal === "create" ? null : modal}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); loadUsers(); }}
        />
      )}
    </div>
  );
}
