"""Panel de administración de productos — protegido por roles (MH-05).

Solo ADMIN o MARKETING pueden crear/editar; solo ADMIN puede eliminar.
Usa IProductWriter (ISP): operaciones de escritura del catálogo.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import container
from app.api.schemas import ProductIn, ProductOut
from app.auth.dependencies import require_roles
from app.auth.roles import Role
from app.domain.entities import Product
from app.domain.exceptions import ProductNotFoundError

router = APIRouter(prefix="/admin/products", tags=["admin"])


@router.post(
    "",
    response_model=ProductOut,
    status_code=201,
    summary="Crear producto (admin/marketing)",
    dependencies=[Depends(require_roles(Role.MARKETING))],
)
def create_product(body: ProductIn):
    product = Product(
        sku=body.sku,
        name=body.name,
        price=body.price,
        category_id=body.category_id,
        description=body.description,
        reorder_point=body.reorder_point,
        is_active=body.is_active,
    )
    saved = container.products.save(product)
    return ProductOut(**saved.to_dict())


@router.put(
    "/{product_id}",
    response_model=ProductOut,
    summary="Actualizar producto (admin/marketing)",
    dependencies=[Depends(require_roles(Role.MARKETING))],
)
def update_product(product_id: int, body: ProductIn):
    existing = container.products.find_by_id(product_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=str(ProductNotFoundError(product_id)))
    existing.sku = body.sku
    existing.name = body.name
    existing.price = body.price
    existing.category_id = body.category_id
    existing.description = body.description
    existing.reorder_point = body.reorder_point
    existing.is_active = body.is_active
    saved = container.products.save(existing)
    return ProductOut(**saved.to_dict())


@router.delete(
    "/{product_id}",
    status_code=204,
    summary="Eliminar producto (solo admin)",
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def delete_product(product_id: int):
    if container.products.find_by_id(product_id) is None:
        raise HTTPException(status_code=404, detail=str(ProductNotFoundError(product_id)))
    container.products.delete(product_id)
