"""
Unit tests for the create_product endpoint and validator.
Run with: pytest test_create_product.py -v
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from validators import validate_product_payload


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------

class TestValidateProductPayload:

    def test_valid_payload(self):
        data = {
            "name": "Widget A",
            "sku": "wid-001",
            "price": "19.99",
            "warehouse_id": 1,
            "initial_quantity": 50,
        }
        result, errors = validate_product_payload(data)
        assert errors == []
        assert result["sku"] == "WID-001"          # SKU uppercased
        assert result["price"] == Decimal("19.99") # Decimal, not float
        assert result["initial_quantity"] == 50

    def test_missing_required_field(self):
        data = {"name": "Widget A", "sku": "WID-001", "price": "9.99"}
        result, errors = validate_product_payload(data)
        assert result is None
        assert any("warehouse_id" in e for e in errors)

    def test_invalid_price(self):
        data = {"name": "A", "sku": "B", "price": "not-a-number", "warehouse_id": 1}
        result, errors = validate_product_payload(data)
        assert result is None
        assert any("price" in e for e in errors)

    def test_negative_price(self):
        data = {"name": "A", "sku": "B", "price": "-5", "warehouse_id": 1}
        result, errors = validate_product_payload(data)
        assert result is None
        assert any("non-negative" in e for e in errors)

    def test_optional_quantity_defaults_to_zero(self):
        data = {"name": "A", "sku": "B", "price": "10.00", "warehouse_id": 1}
        result, errors = validate_product_payload(data)
        assert errors == []
        assert result["initial_quantity"] == 0

    def test_negative_quantity_rejected(self):
        data = {"name": "A", "sku": "B", "price": "10.00", "warehouse_id": 1, "initial_quantity": -3}
        result, errors = validate_product_payload(data)
        assert result is None
        assert any("initial_quantity" in e for e in errors)

    def test_invalid_warehouse_id(self):
        data = {"name": "A", "sku": "B", "price": "10.00", "warehouse_id": "abc"}
        result, errors = validate_product_payload(data)
        assert result is None
        assert any("warehouse_id" in e for e in errors)
