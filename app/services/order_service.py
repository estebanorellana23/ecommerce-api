"""Servicio del proceso de compra (checkout).

Módulo de alto nivel que depende solo de abstracciones (DIP): repositorios,
pasarela de pago y notificador se inyectan desde el contenedor de dependencias.
Reserva stock vía InventoryService para mantener la integridad del inventario.
"""
from __future__ import annotations

from app.domain.entities import Cart, Customer, Order
from app.domain.exceptions import (
    EmptyCartError,
    InsufficientStockError,
    OrderNotFoundError,
    PaymentDeclinedError,
)
from app.payments.gateway import IPaymentGateway
from app.repositories.interfaces import IOrderRepository, IProductReader
from app.services.inventory_service import InventoryService


class OrderService:
    def __init__(
        self,
        order_repo: IOrderRepository,
        product_repo: IProductReader,
        payment: IPaymentGateway,
        inventory: InventoryService,
    ):
        self._orders = order_repo
        self._products = product_repo
        self._payment = payment
        self._inventory = inventory

    def place_order(self, cart: Cart, customer: Customer) -> Order:
        if not cart.items:
            raise EmptyCartError()

        # 1. Validar stock disponible de cada item
        for item in cart.items:
            product = self._products.find_by_id(item.product_id)
            if product is None:
                raise InsufficientStockError(item.product_id, item.quantity, 0)
            stock = self._inventory.get_stock(item.product_id)
            if stock.net_available() < item.quantity:
                raise InsufficientStockError(
                    item.product_id, item.quantity, stock.net_available()
                )

        # 2. Cobrar a través de la pasarela inyectada (DIP/OCP)
        result = self._payment.charge(cart.total(), cart.payment_token or "")
        if not result.success:
            raise PaymentDeclinedError(result.message)

        # 3. Confirmar pedido y descontar inventario (dispara Observers)
        order = Order.from_cart(cart, customer)
        order.confirm(result.transaction_id)
        saved = self._orders.save(order)
        for item in cart.items:
            self._inventory.adjust_stock(
                item.product_id, -item.quantity, reason=f"order:{saved.id}"
            )
        return saved

    def cancel_order(self, order_id: int, reason: str) -> Order:
        order = self._orders.find_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        order.cancel(reason)
        # Reponer inventario de los items cancelados
        for item in order.items:
            self._inventory.adjust_stock(
                item.product_id, item.quantity, reason=f"cancel:{order_id}"
            )
        return self._orders.save(order)

    def get_order(self, order_id: int) -> Order:
        order = self._orders.find_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order
