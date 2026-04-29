"""
GET /api/companies/<company_id>/alerts/low-stock

Returns low-stock alerts for all active products in all active warehouses
belonging to a company, filtered to products with recent sales activity.

Assumptions:
  - g.current_user is injected by an auth middleware before this view runs.
  - The lookback window defaults to 30 days but is configurable via ?lookback_days=N.
  - Low-stock threshold comes from product_types.low_stock_threshold.
    Products with no type use a system default of 10 units.
  - days_until_stockout = current_stock / daily_velocity.
    Returned as null when velocity is zero (no sales but record still exists).
  - Alerts are per warehouse, not aggregated across warehouses.
"""

import logging
import os
from pathlib import Path

from flask import Blueprint, jsonify, g, request
from sqlalchemy import text

from models import db

alerts_bp = Blueprint("alerts", __name__)
logger = logging.getLogger(__name__)

# Load the SQL query from the companion .sql file at import time.
# Keeping SQL in a dedicated file makes it easier to test and review independently.
_QUERY_FILE = Path(__file__).parent / "low_stock_query.sql"
_LOW_STOCK_SQL = _QUERY_FILE.read_text()

DEFAULT_LOOKBACK_DAYS = 30


def _parse_lookback_days(raw: str | None) -> tuple[int, str | None]:
    """
    Parse and validate the ?lookback_days query parameter.
    Returns (value, error_message).
    """
    if raw is None:
        return DEFAULT_LOOKBACK_DAYS, None
    try:
        days = int(raw)
        if days < 1 or days > 365:
            return DEFAULT_LOOKBACK_DAYS, "'lookback_days' must be between 1 and 365"
        return days, None
    except ValueError:
        return DEFAULT_LOOKBACK_DAYS, "'lookback_days' must be an integer"


def _compute_days_until_stockout(current_stock: int, daily_velocity: float) -> int | None:
    """
    Estimate how many days of stock remain given the current quantity
    and the average daily sales velocity.

    Returns None when velocity is zero or not available to avoid division by zero.
    """
    if not daily_velocity or daily_velocity <= 0:
        return None
    return round(current_stock / daily_velocity)


def _build_alert(row) -> dict:
    """Convert a raw DB row into the alert response structure."""
    days_until_stockout = _compute_days_until_stockout(
        current_stock=row["current_stock"],
        daily_velocity=float(row["daily_velocity"]) if row["daily_velocity"] else 0,
    )

    supplier = None
    if row["supplier_id"]:
        supplier = {
            "id": row["supplier_id"],
            "name": row["supplier_name"],
            "contact_email": row["supplier_email"],
        }

    return {
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "sku": row["sku"],
        "warehouse_id": row["warehouse_id"],
        "warehouse_name": row["warehouse_name"],
        "current_stock": row["current_stock"],
        "threshold": row["threshold"],
        "days_until_stockout": days_until_stockout,
        "supplier": supplier,
    }


@alerts_bp.route("/api/companies/<int:company_id>/alerts/low-stock", methods=["GET"])
def get_low_stock_alerts(company_id: int):
    # ------------------------------------------------------------------
    # 1. Authorization: caller must belong to the requested company
    # ------------------------------------------------------------------
    if g.current_user.company_id != company_id:
        return jsonify({"error": "Access denied"}), 403

    # ------------------------------------------------------------------
    # 2. Parse optional query parameters
    # ------------------------------------------------------------------
    lookback_days, param_error = _parse_lookback_days(request.args.get("lookback_days"))
    if param_error:
        return jsonify({"error": param_error}), 400

    # ------------------------------------------------------------------
    # 3. Execute the low-stock query
    # ------------------------------------------------------------------
    try:
        result = db.session.execute(
            text(_LOW_STOCK_SQL),
            {"company_id": company_id, "lookback_days": lookback_days},
        )
        rows = result.mappings().all()

        alerts = [_build_alert(row) for row in rows]

        return jsonify({
            "alerts": alerts,
            "total_alerts": len(alerts),
        }), 200

    except Exception as exc:
        logger.error(
            "Error fetching low-stock alerts for company %d: %s",
            company_id, exc, exc_info=True,
        )
        return jsonify({"error": "Internal server error"}), 500
