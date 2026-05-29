"""Interfaces (puertos) de los repositorios.

Aplica **ISP** (interfaces segregadas de lectura/escritura) y habilita **DIP**:
los servicios dependen de estas abstracciones, no de implementaciones concretas.
Ver nota 07 — Diseño OO, secciones I y D.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities import Customer, Order, Product, StockRecord
from app.domain.value_objects import CatalogPage, SearchFilters


class IProductReader(ABC):
    """Operaciones de solo lectura del catálogo (lo único que necesita el público)."""

    @abstractmethod
    def find_by_id(self, id: int) -> Product | None: ...

    @abstractmethod
    def find_all(self, page: int, size: int) -> CatalogPage: ...

    @abstractmethod
    def search(self, query: str, filters: SearchFilters) -> CatalogPage: ...


class IProductWriter(ABC):
    """Operaciones de escritura del catálogo (administración)."""

    @abstractmethod
    def save(self, product: Product) -> Product: ...

    @abstractmethod
    def delete(self, id: int) -> None: ...

    @abstractmethod
    def bulk_update(self, products: list[Product]) -> None: ...


class IProductRepository(IProductReader, IProductWriter, ABC):
    """Repositorio completo de productos (lectura + escritura)."""


class IInventoryRepository(ABC):
    @abstractmethod
    def get_by_product(self, product_id: int) -> StockRecord | None: ...

    @abstractmethod
    def update(self, record: StockRecord) -> StockRecord: ...

    @abstractmethod
    def find_below_threshold(self, threshold: int) -> list[StockRecord]: ...

    @abstractmethod
    def find_immobilized(self, days_inactive: int) -> list[StockRecord]: ...


class IOrderRepository(ABC):
    @abstractmethod
    def find_by_id(self, id: int) -> Order | None: ...

    @abstractmethod
    def save(self, order: Order) -> Order: ...

    @abstractmethod
    def find_by_customer(self, customer_id: int) -> list[Order]: ...


class ICustomerRepository(ABC):
    @abstractmethod
    def find_by_id(self, id: int) -> Customer | None: ...

    @abstractmethod
    def find_by_email(self, email: str) -> Customer | None: ...

    @abstractmethod
    def save(self, customer: Customer) -> Customer: ...


# --- Soporte para los Observers (SH-01 / SH-04 / MH-06) -------------------


class StockThreshold:
    """Umbral mínimo configurable por producto (tabla stock_thresholds, SH-01)."""

    def __init__(self, product_id: int, minimum: int, reorder_quantity: int):
        self.product_id = product_id
        self.minimum = minimum
        self.reorder_quantity = reorder_quantity


class IThresholdRepository(ABC):
    @abstractmethod
    def get_for_product(self, product_id: int) -> StockThreshold | None: ...

    @abstractmethod
    def set_for_product(self, threshold: StockThreshold) -> StockThreshold: ...


class AuditEntry:
    def __init__(
        self,
        entity: str,
        entity_id: int,
        action: str,
        delta: int,
        timestamp: datetime,
    ):
        self.entity = entity
        self.entity_id = entity_id
        self.action = action
        self.delta = delta
        self.timestamp = timestamp


class IAuditLogRepository(ABC):
    @abstractmethod
    def record(
        self, entity: str, entity_id: int, action: str, delta: int, timestamp: datetime
    ) -> None: ...

    @abstractmethod
    def find_by_product(self, product_id: int, page: int, size: int) -> list[AuditEntry]:
        """Historial de movimientos paginado (SH-04)."""


class ICache(ABC):
    """Abstracción de caché (Redis en producción, memoria en pruebas)."""

    @abstractmethod
    def get(self, key: str) -> dict | None: ...

    @abstractmethod
    def set(self, key: str, value: dict, ttl: int = 60) -> None: ...

    @abstractmethod
    def invalidate(self, key: str) -> None: ...
