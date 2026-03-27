"""
Servicio de gestión de usuarios.
Responsabilidades: crear, actualizar, desactivar usuarios y validar credenciales.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password
from app.models.models import User
from app.repositories.repositories import UserRepository, AuditLogRepository
from app.schemas.schemas import UserCreate, UserUpdate, VALID_ROLES

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)
        self.audit = AuditLogRepository(db)

    # ------------------------------------------------------------------
    # Autenticación
    # ------------------------------------------------------------------

    def authenticate(self, credential: str, password: str) -> Optional[User]:
        """Verifica credenciales. Retorna el User si son válidas, None si no."""
        user = self.repo.get_by_credential(credential)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    # ------------------------------------------------------------------
    # CRUD de usuarios
    # ------------------------------------------------------------------

    def create_user(
        self,
        data: UserCreate,
        actor_id: int,
        actor_username: str,
        ip_address: Optional[str] = None,
    ) -> User:
        if data.role not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Rol inválido '{data.role}'. Opciones: {', '.join(sorted(VALID_ROLES))}.",
            )
        if len(data.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La contraseña debe tener al menos 8 caracteres.",
            )
        if self.repo.get_by_username(data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El username '{data.username}' ya está en uso.",
            )
        if self.repo.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El email '{data.email}' ya está registrado.",
            )

        user = self.repo.create(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            is_active=True,
        )

        self.audit.log(
            action="user.create",
            user_id=actor_id,
            username=actor_username,
            resource_type="user",
            resource_id=str(user.id),
            detail=f"Usuario '{user.username}' creado con rol '{user.role}'.",
            ip_address=ip_address,
        )
        logger.info("Usuario creado: %s (rol=%s) por %s", user.username, user.role, actor_username)
        return user

    def update_user(
        self,
        user_id: int,
        data: UserUpdate,
        actor_id: int,
        actor_username: str,
        ip_address: Optional[str] = None,
    ) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"Usuario id={user_id} no encontrado.")

        if data.role is not None and data.role not in VALID_ROLES:
            raise HTTPException(
                status_code=422,
                detail=f"Rol inválido. Opciones: {', '.join(sorted(VALID_ROLES))}.",
            )
        if data.email and data.email != user.email:
            if self.repo.get_by_email(data.email):
                raise HTTPException(status_code=409, detail="Email ya en uso.")
        if data.password is not None and len(data.password) < 8:
            raise HTTPException(status_code=422, detail="La contraseña debe tener al menos 8 caracteres.")

        changes: dict = {}
        if data.email is not None:
            changes["email"] = data.email
        if data.full_name is not None:
            changes["full_name"] = data.full_name
        if data.role is not None:
            changes["role"] = data.role
        if data.password is not None:
            changes["hashed_password"] = hash_password(data.password)

        updated = self.repo.update(user, **changes)

        self.audit.log(
            action="user.update",
            user_id=actor_id,
            username=actor_username,
            resource_type="user",
            resource_id=str(user_id),
            detail=f"Campos actualizados: {list(changes.keys())}.",
            ip_address=ip_address,
        )
        return updated

    def set_active(
        self,
        user_id: int,
        is_active: bool,
        actor_id: int,
        actor_username: str,
        ip_address: Optional[str] = None,
    ) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"Usuario id={user_id} no encontrado.")
        if user.id == actor_id and not is_active:
            raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta.")

        updated = self.repo.update(user, is_active=is_active)
        action = "user.activate" if is_active else "user.deactivate"
        self.audit.log(
            action=action,
            user_id=actor_id,
            username=actor_username,
            resource_type="user",
            resource_id=str(user_id),
            detail=f"Usuario '{user.username}' {'activado' if is_active else 'desactivado'}.",
            ip_address=ip_address,
        )
        return updated
