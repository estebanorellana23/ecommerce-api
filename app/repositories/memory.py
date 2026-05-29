"""Implementaciones en memoria de los repositorios.

Cumplen el **Principio de Sustitución de Liskov (LSP)**: son intercambiables
con las versiones Postgres en cualquier servicio, lo que permite correr la
suite de pruebas sin levantar una base de datos (acelera el CI/CD — E4).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.entities import Customer, Order, Product, StockRecord, User
from app.domain.value_objects import CatalogPage, SearchFilters
from app.repositories.interfaces import (
    AuditEntry,
    IAuditLogRepository,
    ICustomerRepository,
    IInventoryRepository,
    IOrderRepository,
    IProductRepository,
    IThresholdRepository,
    IUserRepository,
    StockThreshold,
)


class InMemoryProductRepository(IProductRepository):
    def __init__(self, products: list[Product] | None = None):
        self._store: dict[int, Product] = {}
        self._seq = 0
        for p in products or []:
            self.save(p)

    def find_by_id(self, id: int) -> Product | None:
        return self._store.get(id)

    def find_all(self, page: int, size: int) -> CatalogPage:
        items = [p for p in self._store.values() if p.is_active]
        start = (page - 1) * size
        return CatalogPage(
            items=items[start : start + size], total=len(items), page=page, size=size
        )

    def search(self, query: str, filters: SearchFilters) -> CatalogPage:
        q = query.lower().strip()
        results = []
        for p in self._store.values():
            if filters.only_active and not p.is_active:
                continue
            if filters.category_id is not None and p.category_id != filters.category_id:
                continue
            if filters.min_price is not None and p.price < filters.min_price:
                continue
            if filters.max_price is not None and p.price > filters.max_price:
                continue
            haystack = f"{p.name} {p.sku} {p.description}".lower()
            if q == "" or q in haystack:
                results.append(p)
        return CatalogPage(items=results, total=len(results), size=len(results) or 1)

    def save(self, product: Product) -> Product:
        if product.id is None:
            self._seq += 1
            product.id = self._seq
        self._store[product.id] = product
        return product

    def delete(self, id: int) -> None:
        self._store.pop(id, None)

    def bulk_update(self, products: list[Product]) -> None:
        for product in products:
            self.save(product)


class InMemoryInventoryRepository(IInventoryRepository):
    def __init__(self) -> None:
        self._store: dict[int, StockRecord] = {}
        self._last_movement: dict[int, datetime] = {}

    def get_by_product(self, product_id: int) -> StockRecord | None:
        return self._store.get(product_id)

    def update(self, record: StockRecord) -> StockRecord:
        self._store[record.product_id] = record
        self._last_movement[record.product_id] = datetime.now(timezone.utc)
        return record

    def find_below_threshold(self, threshold: int) -> list[StockRecord]:
        return [r for r in self._store.values() if r.available < threshold]

    def find_immobilized(self, days_inactive: int) -> list[StockRecord]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_inactive)
        return [
            r
            for pid, r in self._store.items()
            if self._last_movement.get(pid, datetime.now(timezone.utc)) < cutoff
        ]


class InMemoryOrderRepository(IOrderRepository):
    def __init__(self) -> None:
        self._store: dict[int, Order] = {}
        self._seq = 0

    def find_by_id(self, id: int) -> Order | None:
        return self._store.get(id)

    def save(self, order: Order) -> Order:
        if order.id is None:
            self._seq += 1
            order.id = self._seq
        self._store[order.id] = order
        return order

    def find_by_customer(self, customer_id: int) -> list[Order]:
        return [o for o in self._store.values() if o.customer_id == customer_id]


class InMemoryCustomerRepository(ICustomerRepository):
    def __init__(self, customers: list[Customer] | None = None):
        self._store: dict[int, Customer] = {}
        self._seq = 0
        for c in customers or []:
            self.save(c)

    def find_by_id(self, id: int) -> Customer | None:
        return self._store.get(id)

    def find_by_email(self, email: str) -> Customer | None:
        return next((c for c in self._store.values() if c.email == email), None)

    def save(self, customer: Customer) -> Customer:
        if customer.id is None:
            self._seq += 1
            customer.id = self._seq
        self._store[customer.id] = customer
        return customer


class InMemoryThresholdRepository(IThresholdRepository):
    def __init__(self) -> None:
        self._store: dict[int, StockThreshold] = {}

    def get_for_product(self, product_id: int) -> StockThreshold | None:
        return self._store.get(product_id)

    def set_for_product(self, threshold: StockThreshold) -> StockThreshold:
        self._store[threshold.product_id] = threshold
        return threshold


class InMemoryAuditLogRepository(IAuditLogRepository):
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(
        self, entity: str, entity_id: int, action: str, delta: int, timestamp: datetime
    ) -> None:
        self._entries.append(AuditEntry(entity, entity_id, action, delta, timestamp))

    def find_by_product(self, product_id: int, page: int, size: int) -> list[AuditEntry]:
        matching = [
            e for e in self._entries if e.entity == "inventory" and e.entity_id == product_id
        ]
        matching.sort(key=lambda e: e.timestamp, reverse=True)
        start = (page - 1) * size
        return matching[start : start + size]


class InMemoryUserRepository(IUserRepository):
    def __init__(self, users: list[User] | None = None):
        self._store: dict[int, User] = {}
        self._seq = 0
        for u in users or []:
            self.save(u)

    def find_by_email(self, email: str) -> User | None:
        return next((u for u in self._store.values() if u.email == email), None)

    def save(self, user: User) -> User:
        if user.id is None:
            self._seq += 1
            user.id = self._seq
        self._store[user.id] = user
        return user
