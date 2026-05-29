"""Entidades del dominio del E-Commerce API.

Modelos puros de negocio, sin dependencias de framework ni de base de datos.
Corresponden al paquete ``Domain`` del diagrama de clases (nota 08).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OrderStatus(str, Enum):
    """Estados válidos de un pedido (ver CHECK constraint de la tabla orders)."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class Product:
    sku: str
    name: str
    price: Decimal
    category_id: int
    id: int | None = None
    description: str = ""
    cost_price: Decimal | None = None
    reorder_point: int = 0
    is_active: bool = True
    weight_kg: Decimal | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "price": str(self.price),
            "category_id": self.category_id,
            "reorder_point": self.reorder_point,
            "is_active": self.is_active,
        }


@dataclass
class StockRecord:
    product_id: int
    available: int = 0
    reserved: int = 0
    updated_at: datetime = field(default_factory=_now)

    def net_available(self) -> int:
        """Unidades realmente vendibles (disponibles menos reservadas)."""
        return self.available - self.reserved


@dataclass
class InventoryEvent:
    """Evento de cambio de stock que dispara el patrón Observer."""

    product_id: int
    previous_stock: int
    current_stock: int
    event_type: str  # "sale" | "receipt" | "adjustment" | "return" | "sync"
    timestamp: datetime = field(default_factory=_now)


@dataclass
class Customer:
    email: str
    name: str
    id: int | None = None
    phone: str | None = None
    is_active: bool = True
    email_verified: bool = False
    created_at: datetime = field(default_factory=_now)


@dataclass
class CartItem:
    product_id: int
    quantity: int
    unit_price: Decimal

    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Cart:
    customer_id: int
    items: list[CartItem] = field(default_factory=list)
    payment_token: str | None = None

    def add_item(self, item: CartItem) -> None:
        self.items.append(item)

    def total(self) -> Decimal:
        return sum((item.subtotal() for item in self.items), Decimal("0"))


@dataclass
class OrderItem:
    product_id: int
    quantity: int
    unit_price: Decimal
    order_id: int | None = None

    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Order:
    customer_id: int
    items: list[OrderItem] = field(default_factory=list)
    id: int | None = None
    status: OrderStatus = OrderStatus.PENDING
    total: Decimal = Decimal("0")
    payment_token: str | None = None
    transaction_id: str | None = None
    created_at: datetime = field(default_factory=_now)

    @classmethod
    def from_cart(cls, cart: Cart, customer: Customer) -> Order:
        items = [
            OrderItem(
                product_id=ci.product_id,
                quantity=ci.quantity,
                unit_price=ci.unit_price,
            )
            for ci in cart.items
        ]
        return cls(
            customer_id=customer.id,
            items=items,
            total=cart.total(),
            payment_token=cart.payment_token,
        )

    def confirm(self, transaction_id: str) -> None:
        self.transaction_id = transaction_id
        self.status = OrderStatus.CONFIRMED

    def cancel(self, reason: str) -> None:
        self.status = OrderStatus.CANCELLED
