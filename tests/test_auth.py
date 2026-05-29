"""Pruebas de autenticación y autorización por roles (MH-05)."""
from fastapi.testclient import TestClient

from app.api.deps import container
from app.auth.roles import Role
from app.auth.security import hash_password
from app.domain.entities import User
from app.main import app

client = TestClient(app)

ADMIN = {"username": "admin@empresa.gt", "password": "Admin123!"}


def _token(username: str, password: str) -> str:
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _headers(username: str, password: str) -> dict:
    return {"Authorization": f"Bearer {_token(username, password)}"}


def test_login_ok():
    r = client.post("/auth/login", data=ADMIN)
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_login_credenciales_malas():
    r = client.post("/auth/login", data={"username": "admin@empresa.gt", "password": "x"})
    assert r.status_code == 401


def test_me_devuelve_usuario():
    r = client.get("/auth/me", headers=_headers(**ADMIN))
    body = r.json()
    assert body["email"] == "admin@empresa.gt"
    assert body["role"] == "admin"


def test_endpoint_protegido_sin_token():
    r = client.post("/inventory/sync", json=[])
    assert r.status_code == 401


def test_endpoint_protegido_con_admin():
    r = client.post("/inventory/sync", json=[], headers=_headers(**ADMIN))
    assert r.status_code == 200


def test_rbac_rol_insuficiente_es_403():
    # Creamos un usuario marketing y verificamos que NO puede sincronizar inventario
    container.users.save(
        User(
            email="mkt@empresa.gt",
            name="Mkt",
            role=Role.MARKETING,
            password_hash=hash_password("Mkt123!"),
        )
    )
    headers = _headers("mkt@empresa.gt", "Mkt123!")
    r = client.post("/inventory/sync", json=[], headers=headers)
    assert r.status_code == 403


def test_admin_puede_crear_producto():
    r = client.post(
        "/admin/products",
        json={"sku": "NEW-1", "name": "Producto Nuevo", "price": 99.9, "category_id": 1},
        headers=_headers(**ADMIN),
    )
    assert r.status_code == 201
    assert r.json()["sku"] == "NEW-1"


def test_marketing_puede_crear_pero_no_eliminar():
    container.users.save(
        User(
            email="mkt2@empresa.gt",
            name="Mkt2",
            role=Role.MARKETING,
            password_hash=hash_password("Mkt123!"),
        )
    )
    h = _headers("mkt2@empresa.gt", "Mkt123!")
    created = client.post(
        "/admin/products",
        json={"sku": "MKT-9", "name": "Cosa", "price": 10, "category_id": 1},
        headers=h,
    )
    assert created.status_code == 201
    pid = created.json()["id"]
    # marketing NO puede eliminar (solo admin)
    assert client.delete(f"/admin/products/{pid}", headers=h).status_code == 403
    # admin sí puede
    assert client.delete(f"/admin/products/{pid}", headers=_headers(**ADMIN)).status_code == 204
