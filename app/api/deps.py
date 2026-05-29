"""Contenedor de inyección de dependencias.

Aquí se "cablea" toda la aplicación: se eligen las implementaciones concretas
de cada abstracción y se suscriben los observers al sujeto de inventario.
Es el único lugar que conoce las clases concretas (composición sobre herencia).
"""
from __future__ import annotations

from decimal import Decimal

from app.config import settings
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


class Container:
    """Contenedor singleton que arma el grafo de objetos de la aplicación."""

    def __init__(self) -> None:
        # --- Infraestructura ---
        self.cache = InMemoryCache()

        # --- Repositorios (intercambiables por Postgres — LSP/DIP) ---
        self.products = InMemoryProductRepository()
        self.inventory_repo = InMemoryInventoryRepository()
        self.orders = InMemoryOrderRepository()
        self.customers = InMemoryCustomerRepository()
        self.thresholds = InMemoryThresholdRepository()
        self.audit_log = InMemoryAuditLogRepository()

        # --- Notificaciones (Factory) + alertas ---
        self.notification_config = NotificationConfig(
            purchasing_team_emails=settings.purchasing_emails,
            event_channels={"low_stock": ["email", "push"]},
        )
        self.alert_service = LowStockAlertService(
            NotificationFactory, self.notification_config
        )

        # --- Observer: sujeto + suscriptores ---
        self.inventory_subject = InventorySubject()
        self.inventory_subject.subscribe(
            LowStockObserver(self.alert_service, self.thresholds, self.products)
        )
        self.inventory_subject.subscribe(InventoryAuditObserver(self.audit_log))
        self.inventory_subject.subscribe(CatalogCacheObserver(self.cache))

        # --- Pasarela de pago (Factory) ---
        self.payment_gateway = PaymentGatewayFactory.create(
            settings.payment_provider, PaymentConfig()
        )

        # --- Servicios de negocio ---
        self.product_service = ProductService(self.products)
        self.inventory_service = InventoryService(
            self.inventory_repo, self.inventory_subject
        )
        self.order_service = OrderService(
            self.orders, self.products, self.payment_gateway, self.inventory_service
        )

        self._seed()

    def _seed(self) -> None:
        """Datos de ejemplo para poder probar la API sin base de datos externa."""
        demo = [
            Product(sku="LAP-001", name="Laptop Pro 14", price=Decimal("8999.00"),
                    category_id=1, description="Laptop empresarial 16GB RAM",
                    reorder_point=5),
            Product(sku="MOU-002", name="Mouse Inalámbrico", price=Decimal("149.00"),
                    category_id=2, description="Mouse ergonómico Bluetooth",
                    reorder_point=20),
            Product(sku="TEC-003", name="Teclado Mecánico", price=Decimal("499.00"),
                    category_id=2, description="Teclado mecánico switch rojo",
                    reorder_point=15),
        ]
        for p in self.products.bulk_update(demo) or demo:
            pass
        # Stock inicial y umbrales
        self.inventory_service.adjust_stock(1, 12, reason="carga inicial")
        self.inventory_service.adjust_stock(2, 50, reason="carga inicial")
        self.inventory_service.adjust_stock(3, 8, reason="carga inicial")
        self.thresholds.set_for_product(StockThreshold(1, minimum=5, reorder_quantity=10))
        self.thresholds.set_for_product(StockThreshold(2, minimum=20, reorder_quantity=40))
        self.thresholds.set_for_product(StockThreshold(3, minimum=15, reorder_quantity=30))
        # Cliente demo
        self.customers.save(Customer(email="cliente@demo.gt", name="Cliente Demo"))


# Instancia única usada por los routers
container = Container()
