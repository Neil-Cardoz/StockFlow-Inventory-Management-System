# StockFlow - Backend Engineering Intern Case Study

Solution to the StockFlow inventory management system case study.

## Project Structure

```
stockflow/
├── requirements.txt
├── part1/                        # Code Review and Debugging
│   ├── original_buggy.py         # Original code with issues (reference only)
│   ├── models.py                 # SQLAlchemy models
│   ├── validators.py             # Input validation helpers
│   ├── routes.py                 # Fixed create_product endpoint
│   ├── app.py                    # Flask app factory
│   └── test_create_product.py    # Unit tests for Part 1
├── part2/                        # Database Design
│   └── schema.sql                # Full SQL DDL with indexes and constraints
└── part3/                        # API Implementation
    ├── alerts.py                 # Low-stock alerts endpoint
    ├── low_stock_query.sql       # Core SQL query (CTE-based)
    └── test_alerts.py            # Unit tests for Part 3
```

---

## Part 1: Code Review and Debugging

### Issues Found in Original Code

| # | Issue | Impact |
|---|-------|--------|
| 1 | No input validation | Missing fields cause unhandled 500 errors |
| 2 | No SKU uniqueness check | Silent duplicate SKUs corrupt inventory lookups |
| 3 | Two separate commits | Partial writes leave DB in inconsistent state |
| 4 | Wrong HTTP status codes | 200 returned on success instead of 201 |
| 5 | No authorization | Any caller can write to any warehouse (multi-tenant breach) |
| 6 | Float used for price | Floating-point precision errors corrupt financial data |
| 7 | Optional field not handled | Missing `initial_quantity` causes 500 crash |

### Key Fix: Atomic Transaction

The original code used two `db.session.commit()` calls. If the second failed, the product row existed with no inventory record.

The fix uses `db.session.flush()` to get the product ID in memory, then a single `db.session.commit()` to write both rows atomically.

```python
db.session.add(product)
db.session.flush()          # assigns product.id, no commit yet

db.session.add(inventory)
db.session.commit()         # both rows committed together
```

### Running Part 1

```bash
cd part1
pip install -r ../requirements.txt
pytest test_create_product.py -v
```

---

## Part 2: Database Design

### Schema Overview

```
companies
    └── warehouses
    └── suppliers
    └── products  ──── product_types  (threshold per type)
            └── bundle_components  (self-referencing for bundles)
            └── inventory  ──── inventory_history  (audit log)
```

### Key Design Decisions

- **NUMERIC(12,4) for price** - avoids float precision errors on financial data
- **SKU unique per company** - two tenants can share the same SKU convention
- **inventory_history is append-only** - full audit trail + enables velocity calculation
- **Signed delta column** - positive = stock in, negative = stock out; simplifies sum queries
- **product_types.low_stock_threshold** - configurable per type, no hardcoded values
- **Soft deletes via is_active** - preserves referential integrity and history

### Running the Schema

```bash
psql -U your_user -d stockflow -f part2/schema.sql
```

---

## Part 3: API - Low Stock Alerts

### Endpoint

```
GET /api/companies/{company_id}/alerts/low-stock?lookback_days=30
```

### Response

```json
{
  "alerts": [
    {
      "product_id": 123,
      "product_name": "Widget A",
      "sku": "WID-001",
      "warehouse_id": 456,
      "warehouse_name": "Main Warehouse",
      "current_stock": 5,
      "threshold": 20,
      "days_until_stockout": 12,
      "supplier": {
        "id": 789,
        "name": "Supplier Corp",
        "contact_email": "orders@supplier.com"
      }
    }
  ],
  "total_alerts": 1
}
```

### How It Works

The endpoint runs a single CTE query in three steps:

1. **sales_velocity** - sums units sold per (product, warehouse) over the lookback window, calculates daily average
2. **low_stock** - joins inventory with products, warehouses, and types; filters to below-threshold items with recent sales (INNER JOIN on velocity excludes inactive products)
3. Final SELECT - attaches supplier contact info via LEFT JOIN

### Assumptions

- Recent sales activity = at least one `inventory_history` record with `reason='sale'` in the last N days
- Threshold falls back to 10 units when a product has no type assigned
- `days_until_stockout` is `null` when daily velocity is zero
- Alerts are per warehouse, not aggregated (each warehouse manages its own stock)

### Running Part 3

```bash
cd part3
pip install -r ../requirements.txt
pytest test_alerts.py -v
```

---

## Setup

```bash
# Clone and install dependencies
pip install -r requirements.txt

# Set up the database (PostgreSQL required)
psql -U your_user -d stockflow -f part2/schema.sql

# Run all tests
pytest part1/test_create_product.py part3/test_alerts.py -v
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:password@localhost/stockflow` |
