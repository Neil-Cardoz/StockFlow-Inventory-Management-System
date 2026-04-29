"""
Unit tests for the low-stock alert helpers.
Run with: pytest test_alerts.py -v
"""
import pytest
from alerts import _compute_days_until_stockout, _build_alert, _parse_lookback_days


class TestComputeDaysUntilStockout:

    def test_normal_case(self):
        # 50 units at 5 units/day = 10 days
        assert _compute_days_until_stockout(50, 5.0) == 10

    def test_zero_velocity_returns_none(self):
        assert _compute_days_until_stockout(50, 0) is None

    def test_none_velocity_returns_none(self):
        assert _compute_days_until_stockout(50, None) is None

    def test_zero_stock(self):
        assert _compute_days_until_stockout(0, 5.0) == 0

    def test_fractional_rounds(self):
        # 7 units at 3/day = 2.33 -> rounds to 2
        assert _compute_days_until_stockout(7, 3.0) == 2


class TestParseLookbackDays:

    def test_default_when_none(self):
        value, error = _parse_lookback_days(None)
        assert value == 30
        assert error is None

    def test_valid_value(self):
        value, error = _parse_lookback_days("7")
        assert value == 7
        assert error is None

    def test_invalid_string(self):
        value, error = _parse_lookback_days("abc")
        assert value == 30
        assert error is not None

    def test_out_of_range(self):
        value, error = _parse_lookback_days("500")
        assert value == 30
        assert error is not None


class TestBuildAlert:

    def _make_row(self, **overrides):
        base = {
            "product_id": 1,
            "product_name": "Widget A",
            "sku": "WID-001",
            "warehouse_id": 10,
            "warehouse_name": "Main Warehouse",
            "current_stock": 5,
            "threshold": 20,
            "daily_velocity": 0.5,
            "supplier_id": 100,
            "supplier_name": "Supplier Corp",
            "supplier_email": "orders@supplier.com",
        }
        base.update(overrides)
        return base

    def test_full_alert_with_supplier(self):
        row = self._make_row()
        alert = _build_alert(row)
        assert alert["product_id"] == 1
        assert alert["days_until_stockout"] == 10  # 5 / 0.5
        assert alert["supplier"]["id"] == 100

    def test_no_supplier_returns_none(self):
        row = self._make_row(supplier_id=None, supplier_name=None, supplier_email=None)
        alert = _build_alert(row)
        assert alert["supplier"] is None

    def test_zero_velocity_days_none(self):
        row = self._make_row(daily_velocity=0)
        alert = _build_alert(row)
        assert alert["days_until_stockout"] is None
