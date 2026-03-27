"""
Endpoints de autenticación.

POST /auth/login   →  valida credenciales, retorna JWT
GET  /auth/me      →  retorna el usuario del token actual
POST /auth/logout  →  registra logout en auditoría (el cliente elimina el token)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.models.models import User
from app.repositories.repositories import UserRepository, AuditLogRepository
from app.schemas.schemas import LoginRequest, TokenResponse, UserOut
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión")
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Autentica con username o email + contraseña.
    Retorna un JWT Bearer que debe enviarse en el header `Authorization: Bearer <token>`.
    """
    ip = request.client.host if request.client else None
    audit = AuditLogRepository(db)
    service = UserService(db)

    user = service.authenticate(body.credential, body.password)
    if not user:
        audit.log(
            action="user.login_failed",
            detail=f"Intento fallido para credential='{body.credential}'",
            ip_address=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada. Contacta al administrador.",
        )

    UserRepository(db).set_last_login(user)
    token = create_access_token(user.id, user.username, user.role)

    audit.log(
        action="user.login",
        user_id=user.id,
        username=user.username,
        resource_type="user",
        resource_id=str(user.id),
        detail="Inicio de sesión exitoso.",
        ip_address=ip,
    )
    logger.info("Login: user=%s role=%s ip=%s", user.username, user.role, ip)

    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut, summary="Perfil del usuario actual")
def me(current_user: User = Depends(get_current_user)):
    """Retorna los datos del usuario autenticado."""
    return UserOut.model_validate(current_user)


@router.post("/logout", summary="Cerrar sesión")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registra el logout en auditoría. El cliente es responsable de eliminar el token."""
    ip = request.client.host if request.client else None
    AuditLogRepository(db).log(
        action="user.logout",
        user_id=current_user.id,
        username=current_user.username,
        resource_type="user",
        resource_id=str(current_user.id),
        detail="Cierre de sesión.",
        ip_address=ip,
    )
    return {"message": "Sesión cerrada."}
