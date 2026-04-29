from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal
from datetime import datetime

db = SQLAlchemy()


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    warehouses = db.relationship("Warehouse", back_populates="company")
    products = db.relationship("Product", back_populates="company")


class Warehouse(db.Model):
    __tablename__ = "warehouses"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", back_populates="warehouses")
    inventory = db.relationship("Inventory", back_populates="warehouse")


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        db.UniqueConstraint("company_id", "sku", name="uq_product_sku"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    product_type_id = db.Column(db.Integer, db.ForeignKey("product_types.id"), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    # Use Numeric to avoid floating-point precision issues with prices
    price = db.Column(db.Numeric(12, 4), nullable=False)
    is_bundle = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", back_populates="products")
    inventory = db.relationship("Inventory", back_populates="product")
    supplier = db.relationship("Supplier", back_populates="products")
    product_type = db.relationship("ProductType", back_populates="products")


class Inventory(db.Model):
    __tablename__ = "inventory"
    __table_args__ = (
        db.UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product = db.relationship("Product", back_populates="inventory")
    warehouse = db.relationship("Warehouse", back_populates="inventory")


class ProductType(db.Model):
    __tablename__ = "product_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=10, nullable=False)

    products = db.relationship("Product", back_populates="product_type")


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    contact_email = db.Column(db.String(255))
    contact_phone = db.Column(db.String(50))
    lead_time_days = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    products = db.relationship("Product", back_populates="supplier")
