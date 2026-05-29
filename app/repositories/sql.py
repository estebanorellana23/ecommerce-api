"""Implementaciones SQL de los repositorios (PostgreSQL / SQLite vía SQLAlchemy).

Son intercambiables con las versiones en memoria porque cumplen exactamente las
mismas interfaces (Principio de Sustitución de Liskov). El resto de la aplicación
—servicios, observers, routers— no cambia al usar este backend (DIP).

Cada método abre una sesión de vida corta a partir de un ``sessionmaker``, lo que
mantiene la consistencia con el contenedor singleton sin sesiones colgadas.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth.roles import Role
from app.domain.entities import (
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    StockRecord,
    User,
)
from app.domain.value_objects import CatalogPage, SearchFilters
from app.infrastructure.db.models import (
    CustomerModel,
    InventoryModel,
    InventoryMovementModel,
    OrderItemModel,
    OrderModel,
    ProductModel,
    StockThresholdModel,
    UserModel,
)
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

# Placeholder para customers creados sin contraseña (la columna es NOT NULL).
_UNSET_PASSWORD = "!unset"


# --- Mappers ORM <-> Dominio ------------------------------------------------


def _product_to_domain(m: ProductModel) -> Product:
    return Product(
        id=m.id,
        sku=m.sku,
        name=m.name,
        description=m.description or "",
        price=m.price,
        cost_price=m.cost_price,
        category_id=m.category_id,
        reorder_point=m.reorder_point,
        is_active=m.is_active,
        weight_kg=m.weight_kg,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _stock_to_domain(m: InventoryModel) -> StockRecord:
    return StockRecord(
        product_id=m.product_id,
        available=m.available,
        reserved=m.reserved,
        updated_at=m.updated_at,
    )


def _order_to_domain(m: OrderModel) -> Order:
    return Order(
        id=m.id,
        customer_id=m.customer_id,
        status=OrderStatus(m.status),
        total=m.total,
        payment_token=m.payment_token,
        transaction_id=m.transaction_id,
        created_at=m.created_at,
        items=[
            OrderItem(
                order_id=i.order_id,
                product_id=i.product_id,
                quantity=i.quantity,
                unit_price=i.unit_price,
            )
            for i in m.items
        ],
    )


def _customer_to_domain(m: CustomerModel) -> Customer:
    return Customer(
        id=m.id,
        email=m.email,
        name=m.name,
        phone=m.phone,
        is_active=m.is_active,
        email_verified=m.email_verified,
        created_at=m.created_at,
    )


# --- Repositorios -----------------------------------------------------------


class SqlProductRepository(IProductRepository):
    def __init__(self, session_factory: sessionmaker[Session]):
        self._sf = session_factory

    def find_by_id(self, id: int) -> Product | None:
        with self._sf() as s:
            m = s.get(ProductModel, id)
            return _product_to_domain(m) if m else None

    def find_all(self, page: int, size: int) -> CatalogPage:
        with self._sf() as s:
            base = select(ProductModel).where(ProductModel.is_active.is_(True))
            total = s.scalar(select(func.count()).select_from(base.subquery())) or 0
            rows = s.scalars(
                base.order_by(ProductModel.id).offset((page - 1) * size).limit(size)
            ).all()
            return CatalogPage(
                items=[_product_to_domain(m) for m in rows],
                total=total,
                page=page,
                size=size,
            )

    def search(self, query: str, filters: SearchFilters) -> CatalogPage:
        with self._sf() as s:
            stmt = select(ProductModel)
            if filters.only_active:
                stmt = stmt.where(ProductModel.is_active.is_(True))
            if filters.category_id is not None:
                stmt = stmt.where(ProductModel.category_id == filters.category_id)
            if filters.min_price is not None:
                stmt = stmt.where(ProductModel.price >= filters.min_price)
            if filters.max_price is not None:
                stmt = stmt.where(ProductModel.price <= filters.max_price)
            q = query.strip()
            if q:
                like = f"%{q}%"
                stmt = stmt.where(
                    ProductModel.name.ilike(like)
                    | ProductModel.sku.ilike(like)
                    | ProductModel.description.ilike(like)
                )
            rows = s.scalars(stmt.order_by(ProductModel.id)).all()
            return CatalogPage(
                items=[_product_to_domain(m) for m in rows],
                total=len(rows),
                size=len(rows) or 1,
            )

    def save(self, product: Product) -> Product:
        with self._sf() as s:
            if product.id is not None and (m := s.get(ProductModel, product.id)):
                m.sku = product.sku
                m.name = product.name
                m.description = product.description
                m.price = product.price
                m.cost_price = product.cost_price
                m.category_id = product.category_id
                m.reorder_point = product.reorder_point
                m.is_active = product.is_active
                m.weight_kg = product.weight_kg
            else:
                m = ProductModel(
                    sku=product.sku,
                    name=product.name,
                    description=product.description,
                    price=product.price,
                    cost_price=product.cost_price,
                    category_id=product.category_id,
                    reorder_point=product.reorder_point,
                    is_active=product.is_active,
                    weight_kg=product.weight_kg,
                )
                s.add(m)
            s.commit()
            product.id = m.id
            return product

    def delete(self, id: int) -> None:
        with self._sf() as s:
            if m := s.get(ProductModel, id):
                s.delete(m)
                s.commit()

    def bulk_update(self, products: list[Product]) -> None:
        for product in products:
            self.save(product)


class SqlInventoryRepository(IInventoryRepository):
    def __init__(self, session_factory: sessionmaker[Session]):
        self._sf = session_factory

    def get_by_product(self, product_id: int) -> StockRecord | None:
        with self._sf() as s:
            m = s.scalar(
                select(InventoryModel).where(InventoryModel.product_id == product_id)
            )
            return _stock_to_domain(m) if m else None

    def update(self, record: StockRecord) -> StockRecord:
        with self._sf() as s:
            m = s.scalar(
                select(InventoryModel).where(
                    InventoryModel.product_id == record.product_id
                )
            )
            if m is None:
                m = InventoryModel(product_id=record.product_id)
                s.add(m)
            m.available = record.available
            m.reserved = record.reserved
            m.updated_at = datetime.now(timezone.utc)
            s.commit()
            return _stock_to_domain(m)

    def find_below_threshold(self, threshold: int) -> list[StockRecord]:
        with self._sf() as s:
            rows = s.scalars(
                select(InventoryModel).where(InventoryModel.available < threshold)
            ).all()
            return [_stock_to_domain(m) for m in rows]

    def find_immobilized(self, days_inactive: int) -> list[StockRecord]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_inactive)
        with self._sf() as s:
            rows = s.scalars(
                select(InventoryModel).where(InventoryModel.updated_at < cutoff)
            ).all()
            return [_stock_to_domain(m) for m in rows]


class SqlOrderRepository(IOrderRepository):
    def __init__(self, session_factory: sessionmaker[Session]):
        self._sf = session_factory

    def find_by_id(self, id: int) -> Order | None:
        with self._sf() as s:
            m = s.get(OrderModel, id)
            return _order_to_domain(m) if m else None

    def save(self, order: Order) -> Order:
        with self._sf() as s:
            if order.id is not None and (m := s.get(OrderModel, order.id)):
                m.status = order.status.value
                m.total = order.total
                m.transaction_id = order.transaction_id
            else:
                m = OrderModel(
                    customer_id=order.customer_id,
                    status=order.status.value,
                    subtotal=order.total,
                    total=order.total,
                    payment_token=order.payment_token,
                    transaction_id=order.transaction_id,
                    items=[
                        OrderItemModel(
                            product_id=i.product_id,
                            quantity=i.quantity,
                            unit_price=i.unit_price,
                            subtotal=i.subtotal(),
                        )
                        for i in order.items
                    ],
                )
                s.add(m)
            s.commit()
            return _order_to_domain(m)

    def find_by_customer(self, customer_id: int) -> list[Order]:
        with self._sf() as s:
            rows = s.scalars(
                select(OrderModel)
                .where(OrderModel.customer_id == customer_id)
                .order_by(OrderModel.created_at.desc())
            ).all()
            return [_order_to_domain(m) for m in rows]


class SqlCustomerRepository(ICustomerRepository):
    def __init__(self, session_factory: sessionmaker[Session]):
        self._sf = session_factory

    def find_by_id(self, id: int) -> Customer | None:
        with self._sf() as s:
            m = s.get(CustomerModel, id)
            return _customer_to_domain(m) if m else None

    def find_by_email(self, email: str) -> Customer | None:
        with self._sf() as s:
            m = s.scalar(select(CustomerModel).where(CustomerModel.email == email))
            return _customer_to_domain(m) if m else None

    def save(self, customer: Customer) -> Customer:
        with self._sf() as s:
            if customer.id is not None and (m := s.get(CustomerModel, customer.id)):
                m.email = customer.email
                m.name = customer.name
                m.phone = customer.phone
            else:
                m = CustomerModel(
                    email=customer.email,
                    name=customer.name,
                    phone=customer.phone,
                    password_hash=_UNSET_PASSWORD,
                    is_active=customer.is_active,
                    email_verified=customer.email_verified,
                )
                s.add(m)
            s.commit()
            customer.id = m.id
            return customer


class SqlThresholdRepository(IThresholdRepository):
    def __init__(self, session_factory: sessionmaker[Session]):
        self._sf = session_factory

    def get_for_product(self, product_id: int) -> StockThreshold | None:
        with self._sf() as s:
            m = s.scalar(
                select(StockThresholdModel).where(
                    StockThresholdModel.product_id == product_id
                )
            )
            if m is None:
                return None
            return StockThreshold(m.product_id, m.minimum_stock, m.reorder_quantity)

    def set_for_product(self, threshold: StockThreshold) -> StockThreshold:
        with self._sf() as s:
            m = s.scalar(
                select(StockThresholdModel).where(
                    StockThresholdModel.product_id == threshold.product_id
                )
            )
            if m is None:
                m = StockThresholdModel(product_id=threshold.product_id)
                s.add(m)
            m.minimum_stock = threshold.minimum
            m.reorder_quantity = threshold.reorder_quantity
            s.commit()
            return threshold


class SqlAuditLogRepository(IAuditLogRepository):
    """Historial de movimientos de inventario (SH-04).

    Persiste en ``inventory_movements`` (cuyo CHECK de movement_type coincide con
    los tipos de evento del Observer). El stock antes/después se deriva del estado
    actual del inventario, pues el servicio actualiza la tabla antes de notificar.
    """

    def __init__(self, session_factory: sessionmaker[Session]):
        self._sf = session_factory

    def record(
        self, entity: str, entity_id: int, action: str, delta: int, timestamp: datetime
    ) -> None:
        if entity != "inventory":
            return  # este repositorio solo lleva el historial de inventario
        with self._sf() as s:
            current = s.scalar(
                select(InventoryModel.available).where(
                    InventoryModel.product_id == entity_id
                )
            )
            stock_after = current if current is not None else delta
            s.add(
                InventoryMovementModel(
                    product_id=entity_id,
                    movement_type=action,
                    quantity_delta=delta,
                    stock_before=stock_after - delta,
                    stock_after=stock_after,
                )
            )
            s.commit()

    def find_by_product(self, product_id: int, page: int, size: int) -> list[AuditEntry]:
        with self._sf() as s:
            rows = s.scalars(
                select(InventoryMovementModel)
                .where(InventoryMovementModel.product_id == product_id)
                .order_by(
                    InventoryMovementModel.created_at.desc(),
                    InventoryMovementModel.id.desc(),
                )
                .offset((page - 1) * size)
                .limit(size)
            ).all()
            return [
                AuditEntry(
                    entity="inventory",
                    entity_id=m.product_id,
                    action=m.movement_type,
                    delta=m.quantity_delta,
                    timestamp=m.created_at,
                )
                for m in rows
            ]


class SqlUserRepository(IUserRepository):
    def __init__(self, session_factory: sessionmaker[Session]):
        self._sf = session_factory

    def find_by_email(self, email: str) -> User | None:
        with self._sf() as s:
            m = s.scalar(select(UserModel).where(UserModel.email == email))
            if m is None:
                return None
            return User(
                id=m.id,
                email=m.email,
                name=m.name,
                role=Role(m.role),
                password_hash=m.password_hash,
                is_active=m.is_active,
                created_at=m.created_at,
            )

    def save(self, user: User) -> User:
        with self._sf() as s:
            m = s.scalar(select(UserModel).where(UserModel.email == user.email))
            if m is None:
                m = UserModel(email=user.email)
                s.add(m)
            m.name = user.name
            m.role = user.role.value
            m.password_hash = user.password_hash
            m.is_active = user.is_active
            s.commit()
            user.id = m.id
            return user
