"""Servicio del catálogo de productos.

Depende solo de ``IProductReader`` (ISP): el catálogo público no necesita
operaciones de escritura. Demuestra DIP — no conoce la implementación concreta.
"""
from __future__ import annotations

from app.domain.entities import Product
from app.domain.exceptions import ProductNotFoundError
from app.domain.value_objects import CatalogPage, SearchFilters
from app.repositories.interfaces import IProductReader


class ProductService:
    def __init__(self, repo: IProductReader):
        self._repo = repo

    def get_catalog(self, page: int = 1, size: int = 20) -> CatalogPage:
        return self._repo.find_all(page=page, size=size)

    def search(self, query: str, filters: SearchFilters | None = None) -> CatalogPage:
        return self._repo.search(query, filters or SearchFilters())

    def get_detail(self, id: int) -> Product:
        product = self._repo.find_by_id(id)
        if product is None:
            raise ProductNotFoundError(id)
        return product
