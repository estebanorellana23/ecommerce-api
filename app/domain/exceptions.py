"""Excepciones de dominio del E-Commerce API."""
from __future__ import annotations


class DomainError(Exception):
    """Error base del dominio."""


class ProductNotFoundError(DomainError):
    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Producto no encontrado: id={product_id}")


class OrderNotFoundError(DomainError):
    def __init__(self, order_id: int):
        self.order_id = order_id
        super().__init__(f"Pedido no encontrado: id={order_id}")


class InsufficientStockError(DomainError):
    """Se intentó vender más unidades de las disponibles (regla de inventario)."""

    def __init__(self, product_id: int, requested: int = 0, available: int = 0):
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Stock insuficiente para product_id={product_id}: "
            f"solicitado={requested}, disponible={available}"
        )


class PaymentDeclinedError(DomainError):
    def __init__(self, message: str):
        super().__init__(f"Pago rechazado: {message}")


class EmptyCartError(DomainError):
    def __init__(self):
        super().__init__("No se puede crear un pedido con un carrito vacío")
