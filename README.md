# E-Commerce API — Rediseño con Arquitectura Limpia

> **Proyecto Final — Análisis de Sistemas I** · Universidad Mariano Gálvez
> Curso 12026-1900-032-A · Docente: Ing. Benigno Samuel Soto García
> Problema abordado: *"Falta de mantenimiento en el E-Commerce API"*

Implementación funcional del rediseño documentado en el proyecto: una API de
e-commerce que separa responsabilidades aplicando los principios **SOLID** y los
patrones de diseño **Repository**, **Factory** y **Observer**. Cada pieza de
código traza a un requerimiento de la tabla MoSCoW.

---

## ¿Por qué este rediseño?

El diagnóstico (entrevistas + logs) mostró que el código legacy mezclaba acceso a
datos, reglas de negocio y manejo HTTP en el mismo módulo. Por eso el job de
sincronización fallaba en silencio (error 500 ×12/día) y no se podían implementar
alertas, auditoría ni caché. La solución fue separar responsabilidades.

---

## Arquitectura

```
app/
├── domain/          # Entidades de negocio puras (Product, Order, StockRecord, ...)
├── repositories/    # Interfaces (puertos) + impl. en memoria (memory.py) y SQL (sql.py)
├── services/        # Lógica de negocio (Product, Order, Inventory, Alertas)
├── payments/        # Pasarelas de pago — patrón Factory + OCP
├── notifications/   # Canales de notificación — patrón Factory
├── observers/       # Eventos de inventario — patrón Observer
├── auth/            # Autenticación JWT + roles (MH-05): security, service, deps
├── static/          # Panel de administración web (frontend mínimo)
├── infrastructure/  # Caché + modelos SQLAlchemy (ruta Postgres)
└── api/             # FastAPI: routers, schemas y contenedor de dependencias
```

El flujo de actualización de stock integra los tres patrones:

```
POST /inventory/sync
      → InventoryController (HTTP)
      → InventoryService            (reglas de negocio, depende de IInventoryRepository — DIP)
      → InventoryRepository         (Repository: acceso a datos)
      → InventorySubject.notify()   (Observer)
            ├─ LowStockObserver      → NotificationFactory.create() (Factory)
            ├─ InventoryAuditObserver→ audit_log
            └─ CatalogCacheObserver  → invalida caché
```

---

## Cómo correr

```bash
# 1. Crear entorno e instalar dependencias
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Levantar la API (datos de demo en memoria, sin BD externa)
uvicorn app.main:app --reload

# 3. Abrir la documentación interactiva
#    http://localhost:8000/docs
```

### Panel de administración web

Hay un frontend mínimo (HTML/CSS/JS, sin build) servido por la propia API en
**http://localhost:8000/ui/**. Permite iniciar sesión, gestionar el catálogo
(crear/editar/eliminar productos con control por rol) y operar el inventario
(consulta/ajuste de stock y reporte de stock bajo). Login demo:
`admin@empresa.gt` / `Admin123!`.

### Backend de base de datos

La app soporta dos backends de repositorios, seleccionables con `REPO_BACKEND`:

| `REPO_BACKEND` | Almacenamiento | Uso |
|----------------|----------------|-----|
| `memory` (por defecto) | En memoria, datos demo | Desarrollo rápido y pruebas, sin instalar nada |
| `sql` | SQLAlchemy → PostgreSQL / SQLite | Persistencia real |

Ambos implementan **las mismas interfaces** de repositorio, así que la lógica de
negocio no cambia al alternarlos (esto es el Principio de Sustitución de Liskov).

```bash
# Correr con PostgreSQL
export REPO_BACKEND=sql
export DATABASE_URL="postgresql+psycopg://ecommerce:ecommerce@localhost:5432/ecommerce"
uvicorn app.main:app --reload

# O con SQLite (cero setup, persiste en archivo)
REPO_BACKEND=sql DATABASE_URL="sqlite:///./ecommerce.db" uvicorn app.main:app --reload
```

Al arrancar, la app crea las tablas (`create_all`) y siembra datos demo si el
catálogo está vacío. En PostgreSQL, [`db/schema.sql`](db/schema.sql) agrega además
los **triggers**, **constraints** e **índices GIN (pg_trgm)** documentados en la
gobernanza de datos.

### Con Docker (API + PostgreSQL)

```bash
docker compose up --build
```

Levanta PostgreSQL 16 (inicializado con `db/schema.sql`) y la API con
`REPO_BACKEND=sql` conectada a la base. La API espera a que la BD esté lista
(`healthcheck`).

---

## Pruebas

```bash
pytest --cov=app
```

Las pruebas usan los repositorios **en memoria** (mismas interfaces que la versión
Postgres — esto es justamente el Principio de Sustitución de Liskov en acción), por
lo que corren sin levantar base de datos.

---

## Endpoints principales

| Método | Ruta | Requerimiento | Rol requerido |
|--------|------|---------------|---------------|
| POST | `/auth/login` | MH-05 (login OAuth2 → JWT) | público |
| GET | `/auth/me` | MH-05 | autenticado |
| GET | `/catalog?page=&size=` | MH-03 (paginación + caché) | público |
| GET | `/catalog/search?q=` | MH-04 (búsqueda) | público |
| GET | `/catalog/{id}` | — | público |
| GET | `/inventory/{id}` | — | público |
| POST | `/inventory/sync` | MH-01 / MH-02 (sync ERP con errores) | inventory / admin |
| POST | `/inventory/{id}/adjust` | ajuste manual | inventory / admin |
| GET | `/inventory/reports/low-stock` | SH-01 (alertas) | inventory / purchasing / admin |
| GET | `/inventory/reports/movements/{id}` | SH-04 (historial) | inventory / auditor / purchasing / admin |
| POST | `/orders` | checkout | público (cliente) |
| POST | `/orders/{id}/cancel` | cancelación + reposición | público (cliente) |
| POST/PUT | `/admin/products` | gestión de catálogo | marketing / admin |
| DELETE | `/admin/products/{id}` | eliminar producto | admin |

### Autenticación (MH-05)

La API usa **JWT** (OAuth2 password flow) con **roles**: `admin`, `inventory`,
`marketing`, `purchasing`, `auditor`. Las contraseñas se guardan con **bcrypt
(cost 12)**. Al iniciar se siembra un usuario admin demo
(`admin@empresa.gt` / `Admin123!`, configurable por variables de entorno).

```bash
# 1. Obtener token
curl -s -X POST localhost:8000/auth/login \
  -d "username=admin@empresa.gt&password=Admin123!"

# 2. Usar el token en endpoints protegidos
curl -s -X POST localhost:8000/inventory/sync \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '[{"product_id":1,"available":100}]'
```

En `/docs` usa el botón **Authorize** (esquina superior derecha) para autenticarte
y probar los endpoints protegidos directamente.

---

## Trazabilidad

La correspondencia completa **requerimiento → clase → endpoint** y
**principio SOLID / patrón → código** está en [`docs/traceability.md`](docs/traceability.md).
El diagrama de clases (PlantUML) está en [`docs/class_diagram.puml`](docs/class_diagram.puml).
El esquema de base de datos con triggers y constraints está en [`db/schema.sql`](db/schema.sql).

---

## Stack

- **FastAPI** + **Pydantic** — capa HTTP y validación
- **SQLAlchemy 2.0** — modelos ORM (ruta de producción PostgreSQL)
- **pytest** — pruebas unitarias
- **GitHub Actions** — pipeline CI (lint + test + build)

---

## Equipo

| Rol | Integrante |
|-----|-----------|
| Factibilidad + Gobernanza de Datos | José Estuardo Aquino Q. |
| Técnicas de Captación + MoSCoW + Diseño OO | Esteban Javier Orellana C. |
| Gherkin + UML + DFDs | Estuardo Alexander López S. |
| BPMN + Trazabilidad / DevOps | Didier Javier Mejía A. |
