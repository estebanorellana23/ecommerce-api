"""Endpoints del catálogo público (MH-03 caché/paginación, MH-04 búsqueda)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import container
from app.api.schemas import CatalogPageOut, ProductOut
from app.domain.exceptions import ProductNotFoundError
from app.domain.value_objects import SearchFilters

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _to_page_out(page) -> CatalogPageOut:
    return CatalogPageOut(
        items=[ProductOut(**p.to_dict()) for p in page.items],
        total=page.total,
        page=page.page,
        size=page.size,
        pages=page.pages,
    )


@router.get("", response_model=CatalogPageOut, summary="Listar catálogo paginado")
def list_catalog(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    return _to_page_out(container.product_service.get_catalog(page, size))


@router.get("/search", response_model=CatalogPageOut, summary="Buscar productos")
def search_products(
    q: str = Query("", description="Texto a buscar en nombre, SKU o descripción"),
    category_id: int | None = None,
):
    filters = SearchFilters(category_id=category_id)
    return _to_page_out(container.product_service.search(q, filters))


@router.get("/{product_id}", response_model=ProductOut, summary="Detalle de producto")
def get_product(product_id: int):
    try:
        product = container.product_service.get_detail(product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ProductOut(**product.to_dict())
