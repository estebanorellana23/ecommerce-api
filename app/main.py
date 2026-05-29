"""Punto de entrada de la aplicación FastAPI.

Rediseño del E-Commerce API aplicando SOLID + Repository/Factory/Observer.
Proyecto Final — Análisis de Sistemas I, Universidad Mariano Gálvez.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.routers import admin, auth, catalog, health, inventory, orders
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "API de e-commerce rediseñada con arquitectura limpia. "
        "Implementa los principios SOLID y los patrones Repository, Factory y "
        "Observer. Cada endpoint traza a un requerimiento MoSCoW (ver README)."
    ),
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(inventory.router)
app.include_router(orders.router)
app.include_router(admin.router)


@app.get("/", tags=["root"])
def root():
    return {
        "service": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
    }
