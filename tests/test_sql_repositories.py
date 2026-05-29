"""Pruebas de las implementaciones SQL sobre SQLite en memoria.

Verifican que los repositorios SQL cumplen el mismo contrato que los de memoria
(LSP): catálogo, inventario, órdenes, umbrales y auditoría.
"""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.entities import Customer, Order, OrderItem, Product, StockRecord
from app.domain.value_objects import SearchFilters
from app.infrastructure.db.models import Base
from app.repositories.interfaces import StockThreshold
from app.repositories.sql import (
    SqlAuditLogRepository,
    SqlCustomerRepository,
    SqlInventoryRepository,
    SqlOrderRepository,
    SqlProductRepository,
    SqlThresholdRepository,
)


@pytest.fixture
def sf():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def test_product_save_and_find(sf):
    repo = SqlProductRepository(sf)
    saved = repo.save(Product(sku="X-1", name="Cosa", price=Decimal("10.00"), category_id=1))
    assert saved.id is not None
    found = repo.find_by_id(saved.id)
    assert found.sku == "X-1"


def test_product_pagination_and_search(sf):
    repo = SqlProductRepository(sf)
    repo.save(Product(sku="A-1", name="Laptop", price=Decimal("100"), category_id=1))
    repo.save(Product(sku="B-2", name="Mouse", price=Decimal("20"), category_id=2))
    page = repo.find_all(page=1, size=1)
    assert page.total == 2
    assert len(page.items) == 1
    found = repo.search("lap", SearchFilters())
    assert found.total == 1
    assert found.items[0].sku == "A-1"


def test_inventory_update_and_low_stock(sf):
    repo = SqlInventoryRepository(sf)
    repo.update(StockRecord(product_id=1, available=3))
    repo.update(StockRecord(product_id=2, available=50))
    assert repo.get_by_product(1).available == 3
    low = repo.find_below_threshold(10)
    assert {r.product_id for r in low} == {1}


def test_order_save_with_items(sf):
    repo = SqlOrderRepository(sf)
    order = Order(
        customer_id=1,
        total=Decimal("200.00"),
        transaction_id="tx_1",
        items=[OrderItem(product_id=1, quantity=2, unit_price=Decimal("100.00"))],
    )
    saved = repo.save(order)
    assert saved.id is not None
    fetched = repo.find_by_id(saved.id)
    assert len(fetched.items) == 1
    assert fetched.items[0].quantity == 2


def test_customer_repo(sf):
    repo = SqlCustomerRepository(sf)
    repo.save(Customer(email="a@b.gt", name="Ana"))
    assert repo.find_by_email("a@b.gt").name == "Ana"


def test_threshold_repo(sf):
    repo = SqlThresholdRepository(sf)
    repo.set_for_product(StockThreshold(1, minimum=5, reorder_quantity=10))
    t = repo.get_for_product(1)
    assert t.minimum == 5


def test_audit_records_movement(sf):
    inv = SqlInventoryRepository(sf)
    inv.update(StockRecord(product_id=1, available=8))  # stock actual = 8
    audit = SqlAuditLogRepository(sf)
    from datetime import datetime, timezone

    audit.record("inventory", 1, "adjustment", -2, datetime.now(timezone.utc))
    entries = audit.find_by_product(1, page=1, size=10)
    assert len(entries) == 1
    assert entries[0].delta == -2
    assert entries[0].action == "adjustment"
