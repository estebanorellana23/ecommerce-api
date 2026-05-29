"""Servicio de alertas de stock bajo (SH-01).

Usa la NotificationFactory para enviar por los canales configurados sin acoplarse
a ninguno en particular.
"""
from __future__ import annotations

from app.domain.entities import Product
from app.notifications.handlers import NotificationConfig, NotificationFactory


class LowStockAlertService:
    def __init__(self, factory: type[NotificationFactory], config: NotificationConfig):
        self._factory = factory
        self._config = config

    def alert(self, product: Product, current_stock: int) -> None:
        handlers = self._factory.create_for_event("low_stock", self._config)
        for handler in handlers:
            handler.send(
                subject=f"Stock bajo: {product.name}",
                body=(
                    f"Quedan {current_stock} unidades de '{product.name}' "
                    f"(SKU {product.sku}). Punto de reorden: {product.reorder_point}."
                ),
                recipients=self._config.purchasing_team_emails,
            )
