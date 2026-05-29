"""Servicio de autenticación (MH-05).

Verifica credenciales contra el repositorio de usuarios y emite tokens JWT.
Depende de la abstracción IUserRepository (DIP), no de un backend concreto.
"""
from __future__ import annotations

from app.auth.security import create_access_token, verify_password
from app.domain.entities import User
from app.repositories.interfaces import IUserRepository


class InvalidCredentialsError(Exception):
    def __init__(self) -> None:
        super().__init__("Credenciales inválidas")


class AuthService:
    def __init__(self, users: IUserRepository):
        self._users = users

    def authenticate(self, email: str, password: str) -> User:
        user = self._users.find_by_email(email)
        if user is None or not user.is_active:
            raise InvalidCredentialsError()
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        return user

    def login(self, email: str, password: str) -> str:
        user = self.authenticate(email, password)
        return create_access_token(subject=user.email, role=user.role.value)
