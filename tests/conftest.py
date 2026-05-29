"""Fixtures compartidas para las pruebas (todo en memoria, sin BD externa)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.entities import Customer, Product
from app.infrastructure.cache import InMemoryCache
from app.notifications.handlers import NotificationConfig, NotificationFactory
from app.observers.inventory_observers import (
    CatalogCacheObserver,
    InventoryAuditObserver,
    InventorySubject,
    LowStockObserver,
)
from app.payments.gateway import PaymentConfig, PaymentGatewayFactory
from app.repositories.interfaces import StockThreshold
from app.repositories.memory import (
    InMemoryAuditLogRepository,
    InMemoryCustomerRepository,
    InMemoryInventoryRepository,
    InMemoryOrderRepository,
    InMemoryProductRepository,
    InMemoryThresholdRepository,
)
from app.services.inventory_service import InventoryService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.stock_alert_service import LowStockAlertService


@pytest.fixture
def products_repo():
    repo = InMemoryProductRepository()
    repo.save(Product(sku="A-1", name="Producto A", price=Decimal("100.00"),
                      category_id=1, reorder_point=5))
    repo.save(Product(sku="B-2", name="Producto B", price=Decimal("50.00"),
                      category_id=2, reorder_point=10))
    return repo


@pytest.fixture
def cache():
    return InMemoryCache()


@pytest.fixture
def audit_repo():
    return InMemoryAuditLogRepository()


@pytest.fixture
def thresholds_repo():
    repo = InMemoryThresholdRepository()
    repo.set_for_product(StockThreshold(1, minimum=5, reorder_quantity=10))
    return repo


@pytest.fixture
def inventory_subject(products_repo, thresholds_repo, audit_repo, cache):
    alert = LowStockAlertService(
        NotificationFactory,
        NotificationConfig(purchasing_team_emails=["compras@test.gt"],
                           event_channels={"low_stock": ["email"]}),
    )
    subject = InventorySubject()
    subject.subscribe(LowStockObserver(alert, thresholds_repo, products_repo))
    subject.subscribe(InventoryAuditObserver(audit_repo))
    subject.subscribe(CatalogCacheObserver(cache))
    return subject


@pytest.fixture
def inventory_service(inventory_subject):
    svc = InventoryService(InMemoryInventoryRepository(), inventory_subject)
    svc.adjust_stock(1, 20, reason="setup")
    svc.adjust_stock(2, 30, reason="setup")
    return svc


@pytest.fixture
def product_service(products_repo):
    return ProductService(products_repo)


@pytest.fixture
def customers_repo():
    repo = InMemoryCustomerRepository()
    repo.save(Customer(email="c@test.gt", name="Cliente Test"))
    return repo


@pytest.fixture
def order_service(products_repo, inventory_service):
    gateway = PaymentGatewayFactory.create("visanet", PaymentConfig())
    return OrderService(
        InMemoryOrderRepository(), products_repo, gateway, inventory_service
    )
