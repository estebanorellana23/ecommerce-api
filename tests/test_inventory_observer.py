"""Pruebas del patrón Observer en cambios de inventario (SH-01, SH-04, MH-03)."""
from app.domain.entities import InventoryEvent
from app.observers.inventory_observers import InventorySubject


def test_audit_observer_registra_movimiento(inventory_service, audit_repo):
    inventory_service.adjust_stock(1, -3, reason="venta")
    entries = audit_repo.find_by_product(1, page=1, size=10)
    assert len(entries) >= 1
    assert entries[0].delta == -3


def test_low_stock_observer_dispara_alerta(inventory_service, capsys):
    # Producto 1 tiene umbral mínimo 5; lo bajamos por debajo
    inventory_service.adjust_stock(1, -17, reason="venta grande")  # 20 -> 3
    stock = inventory_service.get_stock(1)
    assert stock.available == 3  # quedó por debajo del umbral (alerta emitida)


def test_cache_observer_invalida(inventory_service, cache):
    cache.set("stock:1", {"available": 20}, ttl=60)
    inventory_service.adjust_stock(1, 5, reason="entrada")
    assert cache.get("stock:1") is None  # invalidada por el observer


def test_observer_aislado_no_rompe_a_los_demas(audit_repo):
    """Un observer que falla no debe impedir que los demás reciban el evento."""

    class FailingObserver:
        def on_stock_changed(self, event):
            raise RuntimeError("boom")

    from app.observers.inventory_observers import InventoryAuditObserver

    subject = InventorySubject()
    subject.subscribe(FailingObserver())
    subject.subscribe(InventoryAuditObserver(audit_repo))
    subject.notify(
        InventoryEvent(product_id=1, previous_stock=10, current_stock=8, event_type="sale")
    )
    assert len(audit_repo.find_by_product(1, 1, 10)) == 1
