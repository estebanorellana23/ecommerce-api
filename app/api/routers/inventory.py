"""Endpoints de inventario (MH-01 sync, MH-02 alertas, SH-01/SH-02/SH-04)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import container
from app.api.schemas import (
    AdjustStockIn,
    MovementOut,
    StockOut,
    StockUpdateIn,
    SyncResultOut,
)
from app.auth.dependencies import require_roles
from app.auth.roles import Role
from app.config import settings
from app.domain.value_objects import StockUpdate

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/{product_id}", response_model=StockOut, summary="Consultar stock")
def get_stock(product_id: int):
    record = container.inventory_service.get_stock(product_id)
    return StockOut(
        product_id=record.product_id,
        available=record.available,
        reserved=record.reserved,
        net_available=record.net_available(),
    )


@router.post(
    "/sync",
    response_model=SyncResultOut,
    summary="Sincronizar desde ERP (MH-01)",
    dependencies=[Depends(require_roles(Role.INVENTORY))],
)
def sync_from_erp(updates: list[StockUpdateIn]):
    domain_updates = [
        StockUpdate(product_id=u.product_id, available=u.available, source=u.source)
        for u in updates
    ]
    result = container.inventory_service.sync_from_erp(domain_updates)
    return SyncResultOut(
        processed=result.processed,
        succeeded=result.succeeded,
        failed=result.failed,
        errors=result.errors,
    )


@router.post(
    "/{product_id}/adjust",
    response_model=StockOut,
    summary="Ajuste manual",
    dependencies=[Depends(require_roles(Role.INVENTORY))],
)
def adjust_stock(product_id: int, body: AdjustStockIn):
    try:
        record = container.inventory_service.adjust_stock(
            product_id, body.delta, body.reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return StockOut(
        product_id=record.product_id,
        available=record.available,
        reserved=record.reserved,
        net_available=record.net_available(),
    )


@router.get(
    "/reports/low-stock",
    response_model=list[StockOut],
    summary="Stock bajo (SH-01)",
    dependencies=[Depends(require_roles(Role.INVENTORY, Role.PURCHASING))],
)
def low_stock(threshold: int = Query(settings.low_stock_default_threshold, ge=0)):
    records = container.inventory_service.low_stock_report(threshold)
    return [
        StockOut(
            product_id=r.product_id,
            available=r.available,
            reserved=r.reserved,
            net_available=r.net_available(),
        )
        for r in records
    ]


@router.get(
    "/reports/movements/{product_id}",
    response_model=list[MovementOut],
    summary="Historial de movimientos paginado (SH-04)",
    dependencies=[Depends(require_roles(Role.INVENTORY, Role.AUDITOR, Role.PURCHASING))],
)
def movements(product_id: int, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    entries = container.audit_log.find_by_product(product_id, page, size)
    return [
        MovementOut(
            product_id=e.entity_id,
            action=e.action,
            delta=e.delta,
            timestamp=e.timestamp.isoformat(),
        )
        for e in entries
    ]
