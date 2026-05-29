"""Pruebas del catálogo (MH-03 paginación, MH-04 búsqueda)."""
import pytest

from app.domain.exceptions import ProductNotFoundError
from app.domain.value_objects import SearchFilters


def test_get_catalog_paginado(product_service):
    page = product_service.get_catalog(page=1, size=1)
    assert page.size == 1
    assert page.total == 2
    assert page.pages == 2
    assert len(page.items) == 1


def test_search_por_nombre(product_service):
    page = product_service.search("Producto A")
    assert page.total == 1
    assert page.items[0].sku == "A-1"


def test_search_filtra_por_categoria(product_service):
    page = product_service.search("", SearchFilters(category_id=2))
    assert page.total == 1
    assert page.items[0].category_id == 2


def test_get_detail_inexistente_lanza_error(product_service):
    with pytest.raises(ProductNotFoundError):
        product_service.get_detail(999)
