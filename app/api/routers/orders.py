"""Endpoints del proceso de compra (checkout)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import container
from app.api.schemas import OrderItemOut, OrderOut, PlaceOrderIn
from app.domain.entities import Cart, CartItem
from app.domain.exceptions import (
    EmptyCartError,
    InsufficientStockError,
    OrderNotFoundError,
    PaymentDeclinedError,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def _to_order_out(order) -> OrderOut:
    return OrderOut(
        id=order.id,
        customer_id=order.customer_id,
        status=order.status.value,
        total=order.total,
        transaction_id=order.transaction_id,
        items=[
            OrderItemOut(
                product_id=i.product_id,
                quantity=i.quantity,
                unit_price=i.unit_price,
                subtotal=i.subtotal(),
            )
            for i in order.items
        ],
    )


@router.post("", response_model=OrderOut, status_code=201, summary="Crear pedido")
def place_order(body: PlaceOrderIn):
    customer = container.customers.find_by_id(body.customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cart = Cart(customer_id=body.customer_id, payment_token=body.payment_token)
    for item in body.items:
        cart.add_item(CartItem(item.product_id, item.quantity, item.unit_price))

    try:
        order = container.order_service.place_order(cart, customer)
    except EmptyCartError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except InsufficientStockError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except PaymentDeclinedError as exc:
        raise HTTPException(status_code=402, detail=str(exc))
    return _to_order_out(order)


@router.get("/{order_id}", response_model=OrderOut, summary="Consultar pedido")
def get_order(order_id: int):
    try:
        order = container.order_service.get_order(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _to_order_out(order)


@router.post("/{order_id}/cancel", response_model=OrderOut, summary="Cancelar pedido")
def cancel_order(order_id: int, reason: str = "solicitud del cliente"):
    try:
        order = container.order_service.cancel_order(order_id, reason)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _to_order_out(order)
