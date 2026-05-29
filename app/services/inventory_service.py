"""Servicio de inventario — orquesta sincronización ERP, ajustes y consultas.

Cada cambio de stock emite un ``InventoryEvent`` a través del ``InventorySubject``
(Observer), que dispara alertas, auditoría e invalidación de caché.
Resuelve MH-01 (sync), MH-02 (errores con alertas) y habilita SH-01/SH-04.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.domain.entities import InventoryEvent, StockRecord
from app.domain.value_objects import StockUpdate, SyncResult
from app.observers.inventory_observers import InventorySubject
from app.repositories.interfaces import IInventoryRepository

logger = logging.getLogger("inventory")


class InventoryService:
    def __init__(self, repo: IInventoryRepository, subject: InventorySubject):
        self._repo = repo
        self._subject = subject

    def get_stock(self, product_id: int) -> StockRecord:
        record = self._repo.get_by_product(product_id)
        if record is None:
            # Producto sin registro de inventario -> se trata como stock 0
            record = StockRecord(product_id=product_id, available=0, reserved=0)
        return record

    def sync_from_erp(self, updates: list[StockUpdate]) -> SyncResult:
        """MH-01/MH-02: aplica updates del ERP capturando errores por item."""
        result = SyncResult(processed=len(updates))
        for update in updates:
            try:
                self._apply_change(
                    product_id=update.product_id,
                    new_available=update.available,
                    event_type="sync",
                )
                result.succeeded += 1
            except Exception as exc:  # un item con error no detiene el lote
                logger.error("Sync falló para product_id=%s: %s", update.product_id, exc)
                result.add_error(update.product_id, str(exc))
        return result

    def adjust_stock(self, product_id: int, delta: int, reason: str) -> StockRecord:
        current = self.get_stock(product_id)
        return self._apply_change(
            product_id=product_id,
            new_available=current.available + delta,
            event_type="adjustment",
        )

    def _apply_change(
        self, product_id: int, new_available: int, event_type: str
    ) -> StockRecord:
        if new_available < 0:
            raise ValueError("El stock disponible no puede quedar negativo")

        previous = self.get_stock(product_id)
        updated = StockRecord(
            product_id=product_id,
            available=new_available,
            reserved=previous.reserved,
            updated_at=datetime.now(timezone.utc),
        )
        if updated.net_available() < 0:
            raise ValueError("available - reserved no puede ser negativo")

        self._repo.update(updated)
        self._subject.notify(
            InventoryEvent(
                product_id=product_id,
                previous_stock=previous.available,
                current_stock=new_available,
                event_type=event_type,
            )
        )
        return updated

    def low_stock_report(self, threshold: int) -> list[StockRecord]:
        return self._repo.find_below_threshold(threshold)

    def immobilized_report(self, days_inactive: int = 90) -> list[StockRecord]:
        """SH-02: productos sin movimiento en N días."""
        return self._repo.find_immobilized(days_inactive)
