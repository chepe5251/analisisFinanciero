"""
Tests para el sistema de permisos RBAC.

Verifica:
- viewer no puede crear facturas (HTTP 403)
- operator no puede aprobar presupuestos (HTTP 403)
- admin puede todas las acciones
- decorator require_permission funciona correctamente
"""
import pytest

from app.core.permissions import check_permission, get_user_permissions
from app.models.models import User


def make_user(role: str) -> User:
    user = User()
    user.id = 1
    user.username = f"test_{role}"
    user.role = role
    user.is_active = True
    return user


class TestCheckPermission:
    def test_admin_can_do_everything(self):
        admin = make_user("admin")
        resources_actions = [
            ("invoices", "create"),
            ("invoices", "approve"),
            ("budgets", "approve"),
            ("accounting", "post"),
            ("accounting", "void"),
            ("reports", "export"),
            ("users", "manage"),
        ]
        for resource, action in resources_actions:
            assert check_permission(admin, resource, action), (
                f"Admin debe poder: {resource}.{action}"
            )

    def test_viewer_cannot_create_invoices(self):
        viewer = make_user("viewer")
        assert not check_permission(viewer, "invoices", "create")

    def test_viewer_cannot_create_budgets(self):
        viewer = make_user("viewer")
        assert not check_permission(viewer, "budgets", "create")

    def test_viewer_can_view(self):
        viewer = make_user("viewer")
        assert check_permission(viewer, "invoices", "view")
        assert check_permission(viewer, "budgets", "view")
        assert check_permission(viewer, "accounting", "view")
        assert check_permission(viewer, "reports", "view")

    def test_operator_cannot_approve_budget(self):
        operator = make_user("operator")
        assert not check_permission(operator, "budgets", "approve")

    def test_operator_cannot_approve_invoices(self):
        operator = make_user("operator")
        assert not check_permission(operator, "invoices", "approve")

    def test_operator_cannot_void_entry(self):
        operator = make_user("operator")
        assert not check_permission(operator, "accounting", "void")

    def test_operator_can_create_invoices(self):
        operator = make_user("operator")
        assert check_permission(operator, "invoices", "create")

    def test_operator_can_post_entries(self):
        operator = make_user("operator")
        assert check_permission(operator, "accounting", "post")

    def test_operator_can_export_reports(self):
        operator = make_user("operator")
        assert check_permission(operator, "reports", "export")


class TestGetUserPermissions:
    def test_returns_all_resources(self):
        admin = make_user("admin")
        perms = get_user_permissions(admin)
        assert "invoices" in perms
        assert "budgets" in perms
        assert "accounting" in perms
        assert "reports" in perms
        assert "users" in perms

    def test_viewer_permissions_structure(self):
        viewer = make_user("viewer")
        perms = get_user_permissions(viewer)
        # viewer puede ver pero no crear/aprobar
        assert perms.get("invoices", {}).get("view") is True
        assert perms.get("invoices", {}).get("create") is False
        assert perms.get("budgets", {}).get("approve") is False


class TestHTTPPermissions:
    def test_viewer_cannot_create_invoice_http(self, client, viewer_token, income_account):
        """Un viewer recibe HTTP 403 al intentar crear una factura."""
        from datetime import datetime
        payload = {
            "invoice_type": "issued",
            "invoice_date": "2024-01-15T00:00:00",
            "counterparty_name": "Cliente Test",
            "lines": [
                {
                    "account_id": income_account.id,
                    "description": "Servicio",
                    "quantity": 1.0,
                    "unit_price": 100.0,
                    "tax_rate": 0.0,
                }
            ],
        }
        resp = client.post(
            "/api/invoices",
            json=payload,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_operator_cannot_approve_budget_http(self, client, operator_token, fiscal_period):
        """Un operator recibe HTTP 403 al intentar aprobar un presupuesto."""
        # Primero crear un presupuesto como admin (simular ID)
        resp = client.post(
            "/api/budgets/999/approve",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client):
        """Sin token, los endpoints protegidos retornan 401."""
        resp = client.get("/api/accounting/accounts")
        assert resp.status_code == 401

    def test_admin_can_create_account(self, client, admin_token):
        """Un admin puede crear cuentas contables."""
        payload = {
            "code": "1001",
            "name": "Caja",
            "account_type": "asset",
            "level": 1,
        }
        resp = client.post(
            "/api/accounting/accounts",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == "1001"
