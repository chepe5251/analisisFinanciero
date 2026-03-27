"""
Router central de la API.
Agrega todos los sub-routers en un único APIRouter que main.py monta bajo /api.
"""
from fastapi import APIRouter
from app.api.routes import uploads, reconciliation, reports, auth, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(uploads.router)
api_router.include_router(reconciliation.router)
api_router.include_router(reports.router)
