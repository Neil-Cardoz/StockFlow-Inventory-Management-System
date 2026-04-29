-- ============================================================
-- StockFlow - Low Stock Alert Query
-- Part 3: Core SQL used by the /alerts/low-stock endpoint
-- ============================================================
-- Parameters:
--   :company_id   INTEGER  - the company to fetch alerts for
--   :lookback_days INTEGER - sales history window (default 30)
-- ============================================================

WITH

-- Step 1: Calculate average daily sales velocity per (product, warehouse)
-- over the lookback window. Only 'sale' events count toward velocity.
-- delta is negative for sales, so ABS() gives units consumed.
sales_velocity AS (
    SELECT
        ih.product_id,
        ih.warehouse_id,
        SUM(ABS(ih.delta))              AS units_sold,
        SUM(ABS(ih.delta)) / :lookback_days::FLOAT AS daily_velocity
    FROM inventory_history ih
    WHERE
        ih.changed_at >= NOW() - (:lookback_days || ' days')::INTERVAL
        AND ih.reason = 'sale'
    GROUP BY
        ih.product_id,
        ih.warehouse_id
),

-- Step 2: Find products whose current stock is below their type threshold
-- AND that have had at least one sale in the lookback window (INNER JOIN).
-- This prevents alerts on stale or discontinued products.
low_stock AS (
    SELECT
        p.id                                AS product_id,
        p.name                              AS product_name,
        p.sku,
        w.id                                AS warehouse_id,
        w.name                              AS warehouse_name,
        i.quantity                          AS current_stock,
        COALESCE(pt.low_stock_threshold, 10) AS threshold,
        sv.daily_velocity,
        p.supplier_id
    FROM inventory i
    JOIN products p             ON p.id = i.product_id
    JOIN warehouses w           ON w.id = i.warehouse_id
    LEFT JOIN product_types pt  ON pt.id = p.product_type_id
    -- INNER JOIN: excludes products with no recent sales activity
    JOIN sales_velocity sv      ON sv.product_id = p.id
                                AND sv.warehouse_id = i.warehouse_id
    WHERE
        w.company_id  = :company_id
        AND p.is_active = TRUE
        AND w.is_active = TRUE
        AND i.quantity  < COALESCE(pt.low_stock_threshold, 10)
)

-- Step 3: Attach supplier contact info for reorder purposes
SELECT
    ls.product_id,
    ls.product_name,
    ls.sku,
    ls.warehouse_id,
    ls.warehouse_name,
    ls.current_stock,
    ls.threshold,
    ls.daily_velocity,
    s.id            AS supplier_id,
    s.name          AS supplier_name,
    s.contact_email AS supplier_email
FROM low_stock ls
LEFT JOIN suppliers s ON s.id = ls.supplier_id
ORDER BY ls.current_stock ASC;
