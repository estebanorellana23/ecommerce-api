"""Pruebas del proceso de compra (checkout) y reglas de inventario."""
from decimal import Decimal

import pytest

from app.domain.entities import Cart, CartItem
from app.domain.exceptions import EmptyCartError, InsufficientStockError


def _cart(customer_id=1, product_id=1, qty=2, price="100.00"):
    cart = Cart(customer_id=customer_id, payment_token="tok_visa_demo")
    cart.add_item(CartItem(product_id, qty, Decimal(price)))
    return cart


def test_place_order_descuenta_inventario(order_service, customers_repo, inventory_service):
    customer = customers_repo.find_by_id(1)
    stock_antes = inventory_service.get_stock(1).available
    order = order_service.place_order(_cart(qty=2), customer)
    assert order.status.value == "confirmed"
    assert order.transaction_id is not None
    assert inventory_service.get_stock(1).available == stock_antes - 2


def test_place_order_sin_stock_falla(order_service, customers_repo):
    customer = customers_repo.find_by_id(1)
    with pytest.raises(InsufficientStockError):
        order_service.place_order(_cart(qty=9999), customer)


def test_place_order_carrito_vacio_falla(order_service, customers_repo):
    customer = customers_repo.find_by_id(1)
    cart = Cart(customer_id=1, payment_token="tok")
    with pytest.raises(EmptyCartError):
        order_service.place_order(cart, customer)


def test_cancel_order_repone_inventario(order_service, customers_repo, inventory_service):
    customer = customers_repo.find_by_id(1)
    stock_antes = inventory_service.get_stock(1).available
    order = order_service.place_order(_cart(qty=3), customer)
    order_service.cancel_order(order.id, reason="prueba")
    assert inventory_service.get_stock(1).available == stock_antes
