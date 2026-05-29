"""Endpoint de salud para health checks del pipeline CI/CD (E4)."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.version}
