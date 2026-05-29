"""Esquemas Pydantic para requests y responses de la API."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    description: str
    price: Decimal
    category_id: int
    reorder_point: int
    is_active: bool


class CatalogPageOut(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    size: int
    pages: int


class StockOut(BaseModel):
    product_id: int
    available: int
    reserved: int
    net_available: int


class StockUpdateIn(BaseModel):
    product_id: int
    available: int = Field(ge=0)
    source: str = "erp"


class SyncResultOut(BaseModel):
    processed: int
    succeeded: int
    failed: int
    errors: list[str]


class AdjustStockIn(BaseModel):
    delta: int
    reason: str = "ajuste manual"


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0)


class PlaceOrderIn(BaseModel):
    customer_id: int
    payment_token: str
    items: list[CartItemIn]


class OrderItemOut(BaseModel):
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderOut(BaseModel):
    id: int
    customer_id: int
    status: str
    total: Decimal
    transaction_id: str | None
    items: list[OrderItemOut]


class MovementOut(BaseModel):
    product_id: int
    action: str
    delta: int
    timestamp: str


# --- Autenticación (MH-05) ---


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    is_active: bool


class ProductIn(BaseModel):
    sku: str
    name: str
    price: Decimal = Field(gt=0)
    category_id: int
    description: str = ""
    reorder_point: int = Field(default=0, ge=0)
    is_active: bool = True
