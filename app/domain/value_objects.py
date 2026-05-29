"""Objetos de valor y DTOs del dominio (inmutables, sin identidad propia)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.entities import Product


@dataclass(frozen=True)
class CatalogPage:
    """Página de resultados del catálogo (paginación — requisito MH-03)."""

    items: list[Product]
    total: int
    page: int = 1
    size: int = 20

    @property
    def pages(self) -> int:
        if self.size <= 0:
            return 0
        return (self.total + self.size - 1) // self.size


@dataclass(frozen=True)
class SearchFilters:
    """Filtros opcionales para el buscador full-text (MH-04)."""

    category_id: int | None = None
    only_active: bool = True
    min_price: Decimal | None = None
    max_price: Decimal | None = None


@dataclass(frozen=True)
class PaymentResult:
    success: bool
    transaction_id: str
    message: str = ""


@dataclass(frozen=True)
class RefundResult:
    success: bool
    refund_id: str
    message: str = ""


@dataclass(frozen=True)
class StockUpdate:
    """Actualización de stock proveniente del ERP (MH-01)."""

    product_id: int
    available: int
    source: str = "erp"


@dataclass
class SyncResult:
    """Resultado de un ciclo de sincronización con el ERP (MH-01/MH-02)."""

    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def add_error(self, product_id: int, message: str) -> None:
        self.failed += 1
        self.errors.append(f"product_id={product_id}: {message}")
