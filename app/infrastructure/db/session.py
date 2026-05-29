"""Configuración del engine y la sesión de SQLAlchemy.

Soporta PostgreSQL en producción y SQLite para pruebas/CI (misma capa ORM).
La selección del backend se controla con ``DATABASE_URL`` (ver app/config.py).
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.infrastructure.db.models import Base

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _build_engine(database_url: str) -> Engine:
    # check_same_thread solo aplica a SQLite (servidor de un solo hilo en dev)
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(database_url, future=True, connect_args=connect_args)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine(settings.database_url)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    return _SessionLocal


def init_db() -> None:
    """Crea las tablas del ORM si no existen.

    En PostgreSQL, ``db/schema.sql`` agrega además los triggers e índices GIN
    (pg_trgm) que no son expresables de forma portable con ``create_all``.
    """
    Base.metadata.create_all(bind=get_engine())
