from decimal import Decimal, InvalidOperation


def validate_product_payload(data: dict) -> tuple[dict | None, list[str]]:
    """
    Validate and coerce the incoming JSON payload for product creation.

    Returns:
        (validated_data, errors)
        - On success: (dict of clean values, [])
        - On failure: (None, [list of error messages])
    """
    errors = []

    # ------------------------------------------------------------------
    # Required field presence check
    # ------------------------------------------------------------------
    required_fields = ["name", "sku", "price", "warehouse_id"]
    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"'{field}' is required")

    if errors:
        return None, errors

    # ------------------------------------------------------------------
    # Price: must be a valid non-negative decimal
    # Using Decimal (not float) to avoid floating-point precision errors
    # ------------------------------------------------------------------
    try:
        price = Decimal(str(data["price"]))
        if price < 0:
            errors.append("'price' must be non-negative")
    except InvalidOperation:
        errors.append("'price' must be a valid decimal number")
        price = None

    # ------------------------------------------------------------------
    # warehouse_id: must be a positive integer
    # ------------------------------------------------------------------
    try:
        warehouse_id = int(data["warehouse_id"])
        if warehouse_id <= 0:
            errors.append("'warehouse_id' must be a positive integer")
    except (ValueError, TypeError):
        errors.append("'warehouse_id' must be an integer")
        warehouse_id = None

    # ------------------------------------------------------------------
    # initial_quantity: optional, defaults to 0
    # ------------------------------------------------------------------
    try:
        quantity = int(data.get("initial_quantity", 0))
        if quantity < 0:
            errors.append("'initial_quantity' must be non-negative")
    except (ValueError, TypeError):
        errors.append("'initial_quantity' must be an integer")
        quantity = None

    if errors:
        return None, errors

    return {
        "name": str(data["name"]).strip(),
        "sku": str(data["sku"]).strip().upper(),
        "price": price,
        "warehouse_id": warehouse_id,
        "initial_quantity": quantity,
        "description": str(data.get("description", "")).strip(),
    }, []
