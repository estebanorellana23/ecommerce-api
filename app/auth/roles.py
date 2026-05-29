"""Roles del sistema para el control de acceso (MH-05).

Derivados de la tabla "Responsable de Datos por Entidad" (nota E1-Cap2 Gobernanza).
"""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"          # acceso total al panel de administración
    INVENTORY = "inventory"  # gestión de inventario y umbrales
    MARKETING = "marketing"  # gestión de catálogo/contenido
    PURCHASING = "purchasing"  # consulta de reportes de compras
    AUDITOR = "auditor"      # solo lectura de auditoría
