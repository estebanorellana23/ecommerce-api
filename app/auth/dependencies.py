"""Dependencias de FastAPI para autenticación y autorización por roles (MH-05).

- ``get_current_user``: valida el JWT y devuelve el usuario autenticado.
- ``require_roles(*roles)``: factory de dependencia que restringe un endpoint a
  uno o varios roles. Si el usuario no tiene un rol permitido, responde 403.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.auth.roles import Role
from app.auth.security import decode_access_token
from app.domain.entities import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No autenticado o token inválido",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    from app.api.deps import container  # import diferido para evitar ciclo

    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise _CREDENTIALS_EXC
    user = container.users.find_by_email(payload["sub"])
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXC
    return user


def require_roles(*allowed: Role):
    """Devuelve una dependencia que exige que el usuario tenga uno de los roles."""

    def checker(user: User = Depends(get_current_user)) -> User:
        # El rol ADMIN tiene acceso total; los demás deben estar en la lista.
        if user.role == Role.ADMIN or user.role in allowed:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Rol '{user.role.value}' sin permiso. "
                f"Requiere: {', '.join(r.value for r in allowed)}"
            ),
        )

    return checker
