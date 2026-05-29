"""Configuración de la aplicación (12-factor: variables de entorno)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    app_name: str = "E-Commerce API"
    version: str = "1.0.0"
    # Backend de repositorios: "memory" (cero setup) o "sql" (SQLAlchemy/Postgres)
    repo_backend: str = field(default_factory=lambda: os.getenv("REPO_BACKEND", "memory"))
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./ecommerce.db")
    )
    payment_provider: str = field(
        default_factory=lambda: os.getenv("PAYMENT_PROVIDER", "visanet")
    )
    low_stock_default_threshold: int = int(os.getenv("LOW_STOCK_THRESHOLD", "10"))
    purchasing_emails: list[str] = field(
        default_factory=lambda: os.getenv(
            "PURCHASING_EMAILS", "compras@empresa.gt"
        ).split(",")
    )


settings = Settings()
