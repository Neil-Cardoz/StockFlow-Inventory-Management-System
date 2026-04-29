import logging
from functools import wraps

from flask import Blueprint, request, jsonify, g
from sqlalchemy.exc import IntegrityError

from models import db, Product, Inventory, Warehouse
from validators import validate_product_payload

products_bp = Blueprint("products", __name__)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Decorator: enforce JSON Content-Type
# ---------------------------------------------------------------------------
def require_json(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# POST /api/products
#
# Issues fixed from the original implementation:
#
# 1. Input validation added  - missing/invalid fields return 400 instead of 500
# 2. SKU uniqueness check    - duplicate SKU returns 409 Conflict
# 3. Authorization check     - warehouse must belong to the caller's company
# 4. Single atomic commit    - db.session.flush() gets product.id, one commit
#                              for both product + inventory rows
# 5. Correct HTTP status     - 201 Created on success, not 200
# 6. Decimal price           - Numeric/Decimal instead of float avoids precision loss
# 7. Optional initial_qty    - defaults to 0 if not provided
# 8. Full error handling     - all exceptions caught, session rolled back
# ---------------------------------------------------------------------------
@products_bp.route("/api/products", methods=["POST"])
@require_json
def create_product():
    data = request.json

    # Step 1: Validate and coerce input fields
    validated, errors = validate_product_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    # Step 2: Check SKU uniqueness within this company
    existing = Product.query.filter_by(
        company_id=g.current_user.company_id,
        sku=validated["sku"]
    ).first()
    if existing:
        return jsonify({"error": f"SKU '{validated['sku']}' already exists"}), 409

    # Step 3: Verify the warehouse exists and belongs to the caller's company
    # Prevents cross-tenant data writes (critical for B2B SaaS multi-tenancy)
    warehouse = Warehouse.query.filter_by(
        id=validated["warehouse_id"],
        company_id=g.current_user.company_id,
        is_active=True
    ).first()
    if not warehouse:
        return jsonify({"error": "Warehouse not found or access denied"}), 404

    # Step 4: Create product and inventory in one atomic transaction
    try:
        product = Product(
            company_id=g.current_user.company_id,
            name=validated["name"],
            sku=validated["sku"],
            price=validated["price"],
            description=validated["description"],
        )
        db.session.add(product)

        # flush() assigns product.id without committing the transaction
        # so inventory can reference it in the same transaction
        db.session.flush()

        inventory = Inventory(
            product_id=product.id,
            warehouse_id=validated["warehouse_id"],
            quantity=validated["initial_quantity"],
        )
        db.session.add(inventory)

        # Single commit: both rows are written or neither is (atomicity)
        db.session.commit()

        logger.info("Product created: id=%d sku=%s", product.id, product.sku)
        return jsonify({"message": "Product created", "product_id": product.id}), 201

    except IntegrityError as exc:
        db.session.rollback()
        logger.warning("IntegrityError creating product: %s", exc)
        # Race condition: another request inserted the same SKU between our check and commit
        return jsonify({"error": "A product with this SKU already exists"}), 409

    except Exception as exc:
        db.session.rollback()
        logger.error("Unexpected error creating product: %s", exc, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
