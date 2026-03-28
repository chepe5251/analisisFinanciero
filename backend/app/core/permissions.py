"""
Sistema de permisos granulares basado en roles.

Complementa el sistema de roles (admin | operator | viewer) con
verificaciones a nivel de recurso + acción.
"""
from functools import wraps
from typing import Set, Dict, Tuple

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.models import User


# ---------------------------------------------------------------------------
# Mapa de permisos: (resource, action) → set de roles permitidos
# ---------------------------------------------------------------------------

PERMISSION_MAP: Dict[Tuple[str, str], Set[str]] = {
    ("invoices", "create"):      {"admin", "operator"},
    ("invoices", "issue"):       {"admin", "operator"},
    ("invoices", "approve"):     {"admin"},
    ("invoices", "view"):        {"admin", "operator", "viewer"},
    ("budgets", "create"):       {"admin", "operator"},
    ("budgets", "approve"):      {"admin"},
    ("budgets", "view"):         {"admin", "operator", "viewer"},
    ("accounting", "create"):    {"admin", "operator"},
    ("accounting", "post"):      {"admin", "operator"},
    ("accounting", "void"):      {"admin"},
    ("accounting", "view"):      {"admin", "operator", "viewer"},
    ("reports", "export"):       {"admin", "operator"},
    ("reports", "view"):         {"admin", "operator", "viewer"},
    ("users", "manage"):         {"admin"},
    ("users", "view"):           {"admin"},
    ("reconciliation", "run"):   {"admin", "operator"},
    ("reconciliation", "view"):  {"admin", "operator", "viewer"},
}

ALL_RESOURCES = sorted({r for r, _ in PERMISSION_MAP.keys()})
ALL_ACTIONS = sorted({a for _, a in PERMISSION_MAP.keys()})


def check_permission(user: User, resource: str, action: str) -> bool:
    """Verifica si el usuario tiene permiso para resource + action."""
    allowed_roles = PERMISSION_MAP.get((resource, action), set())
    return user.role in allowed_roles


def require_permission(resource: str, action: str):
    """
    Dependencia de FastAPI que verifica el permiso antes de ejecutar el endpoint.

    Uso:
        @router.post("/invoices")
        def create_invoice(
            current_user: User = Depends(require_permission("invoices", "create"))
        ):
            ...
    """
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if not check_permission(current_user, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permiso denegado: se requiere permiso '{action}' "
                    f"sobre '{resource}'. Tu rol: '{current_user.role}'."
                ),
            )
        return current_user
    return _check


def get_user_permissions(user: User) -> Dict[str, Dict[str, bool]]:
    """
    Retorna todos los permisos del usuario organizados por recurso.
    Usado por el frontend para mostrar/ocultar funcionalidades.
    """
    result: Dict[str, Dict[str, bool]] = {}
    for (resource, action), allowed_roles in PERMISSION_MAP.items():
        if resource not in result:
            result[resource] = {}
        result[resource][action] = user.role in allowed_roles
    return result
