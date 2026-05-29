"""Pruebas de integración de la API vía TestClient (stack completo)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _admin_headers():
    r = client.post(
        "/auth/login",
        data={"username": "admin@empresa.gt", "password": "Admin123!"},
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_catalog_paginado():
    r = client.get("/catalog", params={"page": 1, "size": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["size"] == 2
    assert "items" in body


def test_search():
    r = client.get("/catalog/search", params={"q": "Laptop"})
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_get_stock():
    r = client.get("/inventory/1")
    assert r.status_code == 200
    assert r.json()["product_id"] == 1


def test_sync_from_erp():
    r = client.post(
        "/inventory/sync",
        json=[{"product_id": 1, "available": 100}],
        headers=_admin_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["succeeded"] == 1
    assert body["failed"] == 0


def test_sync_sin_token_es_401():
    r = client.post("/inventory/sync", json=[{"product_id": 1, "available": 100}])
    assert r.status_code == 401


def test_place_order_flow():
    # consultar precio actual del producto 2 y comprar 1 unidad
    detail = client.get("/catalog/2").json()
    r = client.post(
        "/orders",
        json={
            "customer_id": 1,
            "payment_token": "tok_visa_demo",
            "items": [{"product_id": 2, "quantity": 1, "unit_price": detail["price"]}],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "confirmed"
    assert body["transaction_id"]


def test_order_not_found():
    r = client.get("/orders/99999")
    assert r.status_code == 404
