"""Contenedor de inyección de dependencias.

Aquí se "cablea" toda la aplicación: se eligen las implementaciones concretas
de cada abstracción (en memoria o SQL según ``REPO_BACKEND``) y se suscriben los
observers al sujeto de inventario. Es el único lugar que conoce las clases
concretas; el resto del código depende solo de interfaces (DIP).
"""
from __future__ import annotations

from decimal import Decimal

from app.auth.roles import Role
from app.auth.security import hash_password
from app.auth.service import AuthService
from app.config import settings
from app.domain.entities import Customer, Product, User
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
    InMemoryUserRepository,
)
from app.services.inventory_service import InventoryService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.stock_alert_service import LowStockAlertService

_DEMO_PRODUCTS = [
    dict(sku="LAP-001", name="Laptop Pro 14", price=Decimal("8999.00"), category_id=1,
         description="Laptop empresarial 16GB RAM", reorder_point=5),
    dict(sku="MOU-002", name="Mouse Inalámbrico", price=Decimal("149.00"), category_id=2,
         description="Mouse ergonómico Bluetooth", reorder_point=20),
    dict(sku="TEC-003", name="Teclado Mecánico", price=Decimal("499.00"), category_id=2,
         description="Teclado mecánico switch rojo", reorder_point=15),
]
_DEMO_STOCK = {1: 12, 2: 50, 3: 8}
_DEMO_THRESHOLDS = {1: (5, 10), 2: (20, 40), 3: (15, 30)}


class Container:
    """Contenedor singleton que arma el grafo de objetos de la aplicación."""

    def __init__(self) -> None:
        self.cache = InMemoryCache()

        if settings.repo_backend == "sql":
            self._wire_sql()
        else:
            self._wire_memory()

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

        # --- Autenticación y autorización (MH-05) ---
        self.auth_service = AuthService(self.users)

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

        self._seed_if_empty()
        self._seed_admin()

    def _seed_admin(self) -> None:
        """Crea el usuario admin inicial si no existe (demo/desarrollo)."""
        if self.users.find_by_email(settings.seed_admin_email) is None:
            self.users.save(
                User(
                    email=settings.seed_admin_email,
                    name="Administrador",
                    role=Role.ADMIN,
                    password_hash=hash_password(settings.seed_admin_password),
                )
            )

    def _wire_memory(self) -> None:
        self.products = InMemoryProductRepository()
        self.inventory_repo = InMemoryInventoryRepository()
        self.orders = InMemoryOrderRepository()
        self.customers = InMemoryCustomerRepository()
        self.thresholds = InMemoryThresholdRepository()
        self.audit_log = InMemoryAuditLogRepository()
        self.users = InMemoryUserRepository()

    def _wire_sql(self) -> None:
        from app.infrastructure.db.session import get_sessionmaker, init_db
        from app.repositories.sql import (
            SqlAuditLogRepository,
            SqlCustomerRepository,
            SqlInventoryRepository,
            SqlOrderRepository,
            SqlProductRepository,
            SqlThresholdRepository,
            SqlUserRepository,
        )

        init_db()  # crea las tablas si no existen
        sf = get_sessionmaker()
        self._seed_categories_sql(sf)
        self.products = SqlProductRepository(sf)
        self.inventory_repo = SqlInventoryRepository(sf)
        self.orders = SqlOrderRepository(sf)
        self.customers = SqlCustomerRepository(sf)
        self.thresholds = SqlThresholdRepository(sf)
        self.audit_log = SqlAuditLogRepository(sf)
        self.users = SqlUserRepository(sf)

    @staticmethod
    def _seed_categories_sql(sf) -> None:
        """Garantiza las categorías base (las FK de products las requieren)."""
        from app.infrastructure.db.models import CategoryModel

        with sf() as s:
            if s.get(CategoryModel, 1) is None:
                s.add_all(
                    [
                        CategoryModel(id=1, name="Computadoras", slug="computadoras"),
                        CategoryModel(id=2, name="Accesorios", slug="accesorios"),
                    ]
                )
                s.commit()

    def _seed_if_empty(self) -> None:
        """Carga datos de demo solo si el catálogo está vacío (idempotente)."""
        if self.products.find_all(1, 1).total > 0:
            return
        for data in _DEMO_PRODUCTS:
            self.products.save(Product(**data))
        for product_id, qty in _DEMO_STOCK.items():
            self.inventory_service.adjust_stock(product_id, qty, reason="carga inicial")
        for product_id, (minimum, reorder) in _DEMO_THRESHOLDS.items():
            self.thresholds.set_for_product(
                StockThreshold(product_id, minimum=minimum, reorder_quantity=reorder)
            )
        if self.customers.find_by_email("cliente@demo.gt") is None:
            self.customers.save(Customer(email="cliente@demo.gt", name="Cliente Demo"))


# Instancia única usada por los routers
container = Container()
