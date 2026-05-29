-- ============================================================================
--  E-Commerce API — Esquema de base de datos (PostgreSQL)
--  Fuente: nota E1-Cap2 — Gobernanza de Datos (diccionario de datos + DDL)
--  Incluye constraints, FK, índices y 4 triggers.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    parent_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE products (
    id              SERIAL PRIMARY KEY,
    sku             VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    price           DECIMAL(10,2) NOT NULL CHECK (price > 0),
    cost_price      DECIMAL(10,2) CHECK (cost_price > 0),
    category_id     INTEGER NOT NULL REFERENCES categories(id),
    reorder_point   INTEGER NOT NULL DEFAULT 0 CHECK (reorder_point >= 0),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    weight_kg       DECIMAL(6,3),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE inventory (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL UNIQUE REFERENCES products(id),
    available       INTEGER NOT NULL DEFAULT 0 CHECK (available >= 0),
    reserved        INTEGER NOT NULL DEFAULT 0 CHECK (reserved >= 0),
    last_erp_sync   TIMESTAMP,
    sync_source     VARCHAR(20) DEFAULT 'erp'
                    CHECK (sync_source IN ('erp','manual','api')),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_stock_positive CHECK (available - reserved >= 0)
);

CREATE TABLE inventory_movements (
    id              BIGSERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    movement_type   VARCHAR(20) NOT NULL
                    CHECK (movement_type IN ('sale','receipt','adjustment','return','sync')),
    quantity_delta  INTEGER NOT NULL,
    stock_before    INTEGER NOT NULL,
    stock_after     INTEGER NOT NULL,
    reference_id    VARCHAR(50),
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(200) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    role            VARCHAR(20) NOT NULL
                    CHECK (role IN ('admin','inventory','marketing','purchasing','auditor')),
    password_hash   VARCHAR(256) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE customers (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(200) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    phone           VARCHAR(20),
    password_hash   VARCHAR(256) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMP
);

CREATE TABLE orders (
    id              SERIAL PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','confirmed','processing',
                                      'shipped','delivered','cancelled','refunded')),
    subtotal        DECIMAL(10,2) NOT NULL CHECK (subtotal > 0),
    discount        DECIMAL(10,2) NOT NULL DEFAULT 0,
    shipping_cost   DECIMAL(10,2) NOT NULL DEFAULT 0,
    total           DECIMAL(10,2) NOT NULL CHECK (total > 0),
    payment_token   VARCHAR(200),
    transaction_id  VARCHAR(100) UNIQUE,
    shipping_address JSONB,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE order_items (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price      DECIMAL(10,2) NOT NULL CHECK (unit_price > 0),
    subtotal        DECIMAL(10,2) NOT NULL,
    UNIQUE (order_id, product_id)
);

CREATE TABLE stock_thresholds (
    id               SERIAL PRIMARY KEY,
    product_id       INTEGER NOT NULL UNIQUE REFERENCES products(id),
    minimum_stock    INTEGER NOT NULL CHECK (minimum_stock > 0),
    reorder_quantity INTEGER NOT NULL CHECK (reorder_quantity > 0),
    alert_sent_at    TIMESTAMP,
    updated_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       INTEGER NOT NULL,
    action          VARCHAR(20) NOT NULL
                    CHECK (action IN ('CREATE','UPDATE','DELETE','SYNC')),
    old_values      JSONB,
    new_values      JSONB,
    ip_address      INET,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Índices para performance (resuelve MH-03 y SH-04)
CREATE INDEX idx_products_category    ON products(category_id);
CREATE INDEX idx_products_name_trgm   ON products USING gin(name gin_trgm_ops);
CREATE INDEX idx_inventory_available  ON inventory(available);
CREATE INDEX idx_inv_mov_product_date ON inventory_movements(product_id, created_at DESC);
CREATE INDEX idx_orders_customer      ON orders(customer_id, created_at DESC);
CREATE INDEX idx_orders_status        ON orders(status);
CREATE INDEX idx_audit_entity         ON audit_log(entity_type, entity_id, created_at DESC);

-- Trigger 1: actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_products_updated  BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_inventory_updated BEFORE UPDATE ON inventory
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER trg_orders_updated    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Trigger 2: calcular subtotal en order_items automáticamente
CREATE OR REPLACE FUNCTION calc_order_item_subtotal()
RETURNS TRIGGER AS $$
BEGIN
    NEW.subtotal = NEW.unit_price * NEW.quantity;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_order_items_subtotal BEFORE INSERT OR UPDATE ON order_items
    FOR EACH ROW EXECUTE FUNCTION calc_order_item_subtotal();

-- Trigger 3: validar que el stock no quede negativo
CREATE OR REPLACE FUNCTION validate_inventory_stock()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.available - NEW.reserved < 0 THEN
        RAISE EXCEPTION 'Stock disponible no puede quedar negativo: product_id=%', NEW.product_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_inventory_stock_check BEFORE UPDATE ON inventory
    FOR EACH ROW EXECUTE FUNCTION validate_inventory_stock();
