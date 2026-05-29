# Matriz de Trazabilidad — Requerimiento → Código

Mapea cada requerimiento MoSCoW (nota 06) con la clase y el endpoint que lo implementa.

| Req. MoSCoW | Descripción | Clase / Módulo | Endpoint |
|-------------|-------------|----------------|----------|
| **MH-01** | Sync inventario en tiempo real con ERP | `InventoryService.sync_from_erp()` + `InventorySubject.notify()` | `POST /inventory/sync` |
| **MH-02** | Job de sync con manejo de errores y alertas | `InventoryService.sync_from_erp()` (try/except por item → `SyncResult`) | `POST /inventory/sync` |
| **MH-03** | Carga de catálogo < 3s (caché + paginación) | `ProductService.get_catalog()` + `InMemoryCache` + `CatalogCacheObserver` | `GET /catalog?page=&size=` |
| **MH-04** | Buscador full-text por nombre/SKU/descripción | `IProductReader.search()` + `SearchFilters` | `GET /catalog/search?q=` |
| **MH-06** | Logging de endpoints críticos | `InventoryAuditObserver` + logging | (todos) |
| **SH-01** | Alertas de stock bajo configurables | `LowStockObserver` + `LowStockAlertService` + `NotificationFactory` | `GET /inventory/reports/low-stock` |
| **SH-02** | Reporte de productos inmovilizados (+90 días) | `InventoryService.immobilized_report()` | `GET /inventory/reports/...` |
| **SH-04** | Historial de movimientos paginado | `InventoryAuditObserver` + `IAuditLogRepository.find_by_product()` | `GET /inventory/reports/movements/{id}` |

## Trazabilidad SOLID → Código

| Principio | Evidencia en el código |
|-----------|------------------------|
| **S** — Single Responsibility | `InventoryRepository` (datos), `InventoryService` (negocio), `*Notifier` (notifica), routers (HTTP) separados |
| **O** — Open/Closed | `PaymentGatewayFactory` / `NotificationFactory`: agregar canal o pasarela sin tocar código existente |
| **L** — Liskov Substitution | `InMemory*Repository` sustituye a la versión SQL en cualquier servicio (pruebas sin BD) |
| **I** — Interface Segregation | `IProductReader` / `IProductWriter` separadas; el catálogo público solo depende del reader |
| **D** — Dependency Inversion | `OrderService`/`InventoryService` dependen de interfaces; el wiring concreto vive en `app/api/deps.py` |

## Patrones de diseño → Código

| Patrón | Implementación |
|--------|----------------|
| Repository | `app/repositories/interfaces.py` + `app/repositories/memory.py` + `app/infrastructure/db/models.py` |
| Factory | `app/payments/gateway.py` (`PaymentGatewayFactory`), `app/notifications/handlers.py` (`NotificationFactory`) |
| Observer | `app/observers/inventory_observers.py` (`InventorySubject` + 3 observers) |
