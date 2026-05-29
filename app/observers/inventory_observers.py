"""Patrón Observer para los efectos secundarios del cambio de stock.

Cuando el inventario cambia, varios subsistemas reaccionan sin conocerse entre sí:
alertas (SH-01), auditoría (SH-04/MH-06) e invalidación de caché (MH-03).
Ver nota 07 — Observer.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.domain.entities import InventoryEvent
from app.repositories.interfaces import (
    IAuditLogRepository,
    ICache,
    IProductReader,
    IThresholdRepository,
)
from app.services.stock_alert_service import LowStockAlertService

logger = logging.getLogger("observers")


class IInventoryObserver(ABC):
    @abstractmethod
    def on_stock_changed(self, event: InventoryEvent) -> None: ...


class LowStockObserver(IInventoryObserver):
    """Verifica si el stock cruzó el umbral mínimo y dispara alerta (SH-01)."""

    def __init__(
        self,
        alert_service: LowStockAlertService,
        threshold_repo: IThresholdRepository,
        product_repo: IProductReader,
    ):
        self._alerts = alert_service
        self._thresholds = threshold_repo
        self._products = product_repo

    def on_stock_changed(self, event: InventoryEvent) -> None:
        threshold = self._thresholds.get_for_product(event.product_id)
        if threshold and event.current_stock < threshold.minimum:
            product = self._products.find_by_id(event.product_id)
            if product:
                self._alerts.alert(product, event.current_stock)


class InventoryAuditObserver(IInventoryObserver):
    """Registra cada movimiento en el log de auditoría (SH-04 / MH-06)."""

    def __init__(self, audit_log: IAuditLogRepository):
        self._log = audit_log

    def on_stock_changed(self, event: InventoryEvent) -> None:
        self._log.record(
            entity="inventory",
            entity_id=event.product_id,
            action=event.event_type,
            delta=event.current_stock - event.previous_stock,
            timestamp=event.timestamp,
        )


class CatalogCacheObserver(IInventoryObserver):
    """Invalida la caché del producto cuando cambia su stock (MH-03)."""

    def __init__(self, cache: ICache):
        self._cache = cache

    def on_stock_changed(self, event: InventoryEvent) -> None:
        self._cache.invalidate(f"stock:{event.product_id}")
        self._cache.invalidate(f"product:{event.product_id}")


class InventorySubject:
    """Sujeto observable: gestiona suscriptores y notifica los cambios de stock."""

    def __init__(self) -> None:
        self._observers: list[IInventoryObserver] = []

    def subscribe(self, observer: IInventoryObserver) -> None:
        self._observers.append(observer)

    def unsubscribe(self, observer: IInventoryObserver) -> None:
        self._observers.remove(observer)

    def notify(self, event: InventoryEvent) -> None:
        for observer in self._observers:
            try:
                observer.on_stock_changed(event)
            except Exception as exc:  # un observer que falla no rompe a los demás
                logger.error("Observer %s falló: %s", type(observer).__name__, exc)
