"""
Router central de la API.
Agrega todos los sub-routers en un único APIRouter que main.py monta bajo /api.
"""
from fastapi import APIRouter
from app.api.routes import uploads, reconciliation, reports, auth, users
from app.api.routes import accounting, budgets, invoices, financial_reports, dashboard

api_router = APIRouter()

# Módulos originales
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(uploads.router)
api_router.include_router(reconciliation.router)
api_router.include_router(reports.router)

# Módulos nuevos
api_router.include_router(accounting.router)
api_router.include_router(budgets.router)
api_router.include_router(invoices.router)
api_router.include_router(financial_reports.router)
api_router.include_router(dashboard.router)
