"""SQLAlchemy database models."""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, date
import enum
from src.database.connection import Base


class CustomerType(str, enum.Enum):
    """Customer type enumeration."""
    OEM = "OEM"
    AFTERMARKET = "AFTERMARKET"


class LifecycleStatus(str, enum.Enum):
    """Product lifecycle status."""
    ACTIVE = "ACTIVE"
    DISCONTINUED = "DISCONTINUED"
    PHASE_OUT = "PHASE_OUT"


class SegmentationGroup(str, enum.Enum):
    """ABC/XYZ segmentation groups."""
    AX = "AX"
    AY = "AY"
    AZ = "AZ"
    BX = "BX"
    BY = "BY"
    BZ = "BZ"
    CX = "CX"
    CY = "CY"
    CZ = "CZ"


class SKUMaster(Base):
    """Product master data table."""
    __tablename__ = "sku_master"
    
    sku_id = Column(String(50), primary_key=True, index=True)
    category = Column(String(100), nullable=True)
    family = Column(String(100), nullable=True)
    unit_cost = Column(Float, nullable=False)
    lifecycle_status = Column(SQLEnum(LifecycleStatus), default=LifecycleStatus.ACTIVE)
    criticality = Column(String(10), nullable=True)  # A, B, C
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sales_history = relationship("SalesHistory", back_populates="sku")
    inventory = relationship("Inventory", back_populates="sku")
    purchase_orders = relationship("PurchaseOrder", back_populates="sku")
    forecasts = relationship("Forecast", back_populates="sku")
    order_recommendations = relationship("OrderRecommendation", back_populates="sku")
    segmentation = relationship("Segmentation", back_populates="sku", uselist=False)


class SalesHistory(Base):
    """Sales history table."""
    __tablename__ = "sales_history"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku_id = Column(String(50), ForeignKey("sku_master.sku_id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    units_sold = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    customer_type = Column(SQLEnum(CustomerType), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sku = relationship("SKUMaster", back_populates="sales_history")
    
    __table_args__ = (
        {"comment": "Historical sales data at daily/monthly granularity"},
    )


class Inventory(Base):
    """Current inventory levels table."""
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku_id = Column(String(50), ForeignKey("sku_master.sku_id"), nullable=False, index=True)
    stock_level = Column(Float, nullable=False, default=0.0)
    warehouse = Column(String(100), nullable=True)
    safety_stock = Column(Float, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sku = relationship("SKUMaster", back_populates="inventory")


class Supplier(Base):
    """Supplier master data table."""
    __tablename__ = "suppliers"
    
    supplier_id = Column(String(50), primary_key=True, index=True)
    supplier_name = Column(String(200), nullable=False)
    country = Column(String(50), nullable=False)  # BR, CN, DE, US, etc.
    supplier_type = Column(String(50), nullable=True)  # STRATEGIC, STANDARD
    base_lead_time_days = Column(Integer, nullable=False)  # Base lead time
    lead_time_std_days = Column(Integer, nullable=True)  # Lead time variability
    on_time_percentage = Column(Float, nullable=True)  # Reliability metric
    min_order_quantity = Column(Float, nullable=True)  # MOQ
    is_strategic = Column(Boolean, default=False)  # ~5 strategic suppliers
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier_ref")


class PurchaseOrder(Base):
    """Purchase orders and procurement data table."""
    __tablename__ = "purchase_orders"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku_id = Column(String(50), ForeignKey("sku_master.sku_id"), nullable=False, index=True)
    supplier_id = Column(String(50), ForeignKey("suppliers.supplier_id"), nullable=True, index=True)
    order_date = Column(Date, nullable=False, index=True)
    expected_arrival_date = Column(Date, nullable=True)
    actual_arrival_date = Column(Date, nullable=True)
    lead_time_days = Column(Integer, nullable=True)
    quantity_ordered = Column(Float, nullable=False)
    supplier = Column(String(100), nullable=True)  # Legacy field for compatibility
    status = Column(String(20), default="PENDING")  # PENDING, IN_TRANSIT, RECEIVED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sku = relationship("SKUMaster", back_populates="purchase_orders")
    supplier_ref = relationship("Supplier", back_populates="purchase_orders")


class Segmentation(Base):
    """ABC/XYZ segmentation results table."""
    __tablename__ = "segmentation"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku_id = Column(String(50), ForeignKey("sku_master.sku_id"), nullable=False, unique=True, index=True)
    abc_class = Column(String(1), nullable=False)  # A, B, C
    xyz_class = Column(String(1), nullable=False)  # X, Y, Z
    segment_group = Column(SQLEnum(SegmentationGroup), nullable=False)
    annual_revenue = Column(Float, nullable=True)
    coefficient_of_variation = Column(Float, nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sku = relationship("SKUMaster", back_populates="segmentation")


class Forecast(Base):
    """Forecast results table."""
    __tablename__ = "forecasts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku_id = Column(String(50), ForeignKey("sku_master.sku_id"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False, index=True)
    predicted_units = Column(Float, nullable=False)
    confidence_level = Column(Float, nullable=True)  # 0-1
    model_type = Column(String(50), nullable=True)
    model_version = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sku = relationship("SKUMaster", back_populates="forecasts")


class OrderRecommendation(Base):
    """Order recommendations table."""
    __tablename__ = "order_recommendations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku_id = Column(String(50), ForeignKey("sku_master.sku_id"), nullable=False, index=True)
    recommended_qty = Column(Float, nullable=False)
    confidence_level = Column(Float, nullable=True)  # 0-1
    explanation = Column(Text, nullable=True)
    reorder_point = Column(Float, nullable=True)
    safety_stock = Column(Float, nullable=True)
    current_inventory = Column(Float, nullable=True)
    in_transit_qty = Column(Float, nullable=True)
    priority = Column(Integer, nullable=True)  # Based on ABC classification
    status = Column(String(20), default="PENDING")  # PENDING, APPROVED, OVERRIDDEN, EXECUTED
    override_qty = Column(Float, nullable=True)
    override_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sku = relationship("SKUMaster", back_populates="order_recommendations")


class ModelRegistry(Base):
    """Model registry for tracking trained models."""
    __tablename__ = "model_registry"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku_id = Column(String(50), ForeignKey("sku_master.sku_id"), nullable=False, index=True)
    model_type = Column(String(50), nullable=False)
    model_version = Column(String(50), nullable=False)
    model_path = Column(String(500), nullable=False)
    training_date = Column(DateTime, nullable=False)
    validation_mape = Column(Float, nullable=True)
    validation_mae = Column(Float, nullable=True)
    validation_rmse = Column(Float, nullable=True)
    validation_bias = Column(Float, nullable=True)
    validation_mase = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    model_metadata = Column(Text, nullable=True)  # JSON string for additional metadata (renamed from 'metadata' - reserved in SQLAlchemy)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    """User accounts for role-based access control."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # PLANNER, PURCHASING, EXECUTIVE, ADMIN
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

