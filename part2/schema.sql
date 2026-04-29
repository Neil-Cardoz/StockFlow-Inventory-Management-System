-- ============================================================
-- StockFlow - Database Schema
-- Part 2: Database Design
-- ============================================================
-- Design decisions:
--   - NUMERIC(12,4) for prices to avoid float precision errors
--   - SKU unique per company (not globally) for multi-tenant flexibility
--   - inventory_history is append-only for full audit trail + velocity calc
--   - Soft deletes via is_active flags on products and warehouses
--   - product_types stores configurable low_stock_threshold per type
-- ============================================================


-- ------------------------------------------------------------
-- Companies (tenants in the SaaS platform)
-- ------------------------------------------------------------
CREATE TABLE companies (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- Warehouses: each belongs to one company
-- ------------------------------------------------------------
CREATE TABLE warehouses (
    id          SERIAL PRIMARY KEY,
    company_id  INTEGER      NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    address     TEXT,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_warehouses_company ON warehouses(company_id);


-- ------------------------------------------------------------
-- Product types: drives low-stock threshold logic
-- e.g. 'raw_material', 'finished_good', 'consumable'
-- ------------------------------------------------------------
CREATE TABLE product_types (
    id                  SERIAL       PRIMARY KEY,
    name                VARCHAR(100) NOT NULL UNIQUE,
    low_stock_threshold INTEGER      NOT NULL DEFAULT 10
);


-- ------------------------------------------------------------
-- Suppliers: external vendors that supply products to companies
-- ------------------------------------------------------------
CREATE TABLE suppliers (
    id              SERIAL       PRIMARY KEY,
    company_id      INTEGER      NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    contact_email   VARCHAR(255),
    contact_phone   VARCHAR(50),
    -- Average days from purchase order to delivery
    lead_time_days  INTEGER,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_suppliers_company ON suppliers(company_id);


-- ------------------------------------------------------------
-- Users (minimal; full auth is assumed in a separate service)
-- ------------------------------------------------------------
CREATE TABLE users (
    id          SERIAL       PRIMARY KEY,
    company_id  INTEGER      NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    email       VARCHAR(255) NOT NULL UNIQUE,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- Products: belong to a company, reference a type and supplier
-- SKU is unique per company (not globally across all tenants)
-- Price stored as NUMERIC to avoid float precision errors
-- ------------------------------------------------------------
CREATE TABLE products (
    id              SERIAL          PRIMARY KEY,
    company_id      INTEGER         NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    product_type_id INTEGER         REFERENCES product_types(id),
    supplier_id     INTEGER         REFERENCES suppliers(id) ON DELETE SET NULL,
    name            VARCHAR(255)    NOT NULL,
    sku             VARCHAR(100)    NOT NULL,
    description     TEXT,
    price           NUMERIC(12, 4)  NOT NULL,
    is_bundle       BOOLEAN         NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_product_sku UNIQUE (company_id, sku)
);

CREATE INDEX idx_products_company  ON products(company_id);
CREATE INDEX idx_products_supplier ON products(supplier_id);
CREATE INDEX idx_products_type     ON products(product_type_id);


-- ------------------------------------------------------------
-- Bundle components: self-referencing join table
-- A bundle product is made up of one or more component products
-- Constraints prevent a product from being its own component
-- Application layer should prevent circular bundle references
-- ------------------------------------------------------------
CREATE TABLE bundle_components (
    id           SERIAL  PRIMARY KEY,
    bundle_id    INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity     INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),

    CONSTRAINT uq_bundle_component UNIQUE (bundle_id, component_id),
    CONSTRAINT chk_no_self_bundle  CHECK  (bundle_id <> component_id)
);

CREATE INDEX idx_bundle_components_bundle    ON bundle_components(bundle_id);
CREATE INDEX idx_bundle_components_component ON bundle_components(component_id);


-- ------------------------------------------------------------
-- Inventory: current stock of a product at a specific warehouse
-- One row per (product, warehouse) pair
-- quantity CHECK ensures stock never goes negative in the DB
-- ------------------------------------------------------------
CREATE TABLE inventory (
    id           SERIAL    PRIMARY KEY,
    product_id   INTEGER   NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id INTEGER   NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    quantity     INTEGER   NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    updated_at   TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_inventory_product_warehouse UNIQUE (product_id, warehouse_id)
);

CREATE INDEX idx_inventory_product   ON inventory(product_id);
CREATE INDEX idx_inventory_warehouse ON inventory(warehouse_id);


-- ------------------------------------------------------------
-- Inventory history: append-only audit log of every stock change
--
-- delta is signed:
--   positive = stock received  (purchase order, manual adjustment up)
--   negative = stock consumed  (sale, write-off, transfer out)
--
-- reason examples: 'sale', 'purchase_order', 'adjustment', 'transfer_in', 'transfer_out'
-- reference_id links to an order or PO id in an external system
-- ------------------------------------------------------------
CREATE TABLE inventory_history (
    id             BIGSERIAL    PRIMARY KEY,
    inventory_id   INTEGER      NOT NULL REFERENCES inventory(id),
    product_id     INTEGER      NOT NULL REFERENCES products(id),
    warehouse_id   INTEGER      NOT NULL REFERENCES warehouses(id),
    delta          INTEGER      NOT NULL,
    quantity_after INTEGER      NOT NULL,
    reason         VARCHAR(100),
    reference_id   INTEGER,
    changed_by     INTEGER      REFERENCES users(id),
    changed_at     TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- Composite index for velocity queries: product + warehouse + date range
CREATE INDEX idx_inv_history_product_warehouse ON inventory_history(product_id, warehouse_id);
CREATE INDEX idx_inv_history_changed_at        ON inventory_history(changed_at DESC);
