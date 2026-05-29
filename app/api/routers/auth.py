"""Endpoints de autenticación (MH-05)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import container
from app.api.schemas import TokenOut, UserOut
from app.auth.dependencies import get_current_user
from app.auth.service import InvalidCredentialsError
from app.domain.entities import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut, summary="Iniciar sesión (OAuth2)")
def login(form: OAuth2PasswordRequestForm = Depends()):
    # OAuth2 usa el campo 'username'; aquí es el email del usuario.
    try:
        token = container.auth_service.login(form.username, form.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut, summary="Usuario autenticado actual")
def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
    )
