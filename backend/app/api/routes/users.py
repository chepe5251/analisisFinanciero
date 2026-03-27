"""
Endpoints de gestión de usuarios (solo admin).

GET    /users          →  listar usuarios
POST   /users          →  crear usuario
GET    /users/{id}     →  detalle
PUT    /users/{id}     →  actualizar
PATCH  /users/{id}/deactivate  →  desactivar
PATCH  /users/{id}/activate    →  reactivar
GET    /audit          →  log de auditoría
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.models import User
from app.repositories.repositories import AuditLogRepository
from app.schemas.schemas import UserCreate, UserUpdate, UserOut, AuditLogOut
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["users"])

_admin = require_roles("admin")


@router.get("/users", response_model=List[UserOut], summary="Listar usuarios")
def list_users(
    current_user: User = Depends(_admin),
    db: Session = Depends(get_db),
):
    from app.repositories.repositories import UserRepository
    return [UserOut.model_validate(u) for u in UserRepository(db).get_all()]


@router.post("/users", response_model=UserOut, status_code=201, summary="Crear usuario")
def create_user(
    body: UserCreate,
    request: Request,
    current_user: User = Depends(_admin),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    service = UserService(db)
    user = service.create_user(body, current_user.id, current_user.username, ip)
    return UserOut.model_validate(user)


@router.get("/users/{user_id}", response_model=UserOut, summary="Detalle de usuario")
def get_user(
    user_id: int,
    current_user: User = Depends(_admin),
    db: Session = Depends(get_db),
):
    from app.repositories.repositories import UserRepository
    from fastapi import HTTPException
    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuario id={user_id} no encontrado.")
    return UserOut.model_validate(user)


@router.put("/users/{user_id}", response_model=UserOut, summary="Actualizar usuario")
def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    current_user: User = Depends(_admin),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    service = UserService(db)
    user = service.update_user(user_id, body, current_user.id, current_user.username, ip)
    return UserOut.model_validate(user)


@router.patch("/users/{user_id}/deactivate", response_model=UserOut, summary="Desactivar usuario")
def deactivate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(_admin),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    service = UserService(db)
    user = service.set_active(user_id, False, current_user.id, current_user.username, ip)
    return UserOut.model_validate(user)


@router.patch("/users/{user_id}/activate", response_model=UserOut, summary="Activar usuario")
def activate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(_admin),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    service = UserService(db)
    user = service.set_active(user_id, True, current_user.id, current_user.username, ip)
    return UserOut.model_validate(user)


@router.get("/audit", response_model=List[AuditLogOut], summary="Log de auditoría")
def get_audit_log(
    current_user: User = Depends(_admin),
    db: Session = Depends(get_db),
):
    """Últimas 500 entradas del log de auditoría."""
    return [AuditLogOut.model_validate(e) for e in AuditLogRepository(db).get_all(limit=500)]
