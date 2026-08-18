"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime


class ForecastResponse(BaseModel):
    """Forecast response schema."""
    sku_id: str
    forecast_date: date
    predicted_units: float
    confidence_level: Optional[float] = None
    model_type: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderRecommendationResponse(BaseModel):
    """Order recommendation response schema."""
    sku_id: str
    recommended_qty: float
    confidence_level: Optional[float] = None
    explanation: Optional[str] = None
    priority: Optional[int] = None
    reorder_point: Optional[float] = None
    safety_stock: Optional[float] = None
    current_inventory: Optional[float] = None
    in_transit: Optional[float] = None
    
    class Config:
        from_attributes = True


class InventoryStatusResponse(BaseModel):
    """Inventory status response schema."""
    sku_id: str
    stock_level: float
    warehouse: Optional[str] = None
    safety_stock: Optional[float] = None
    
    class Config:
        from_attributes = True


class SegmentationResponse(BaseModel):
    """Segmentation response schema."""
    sku_id: str
    abc_class: str
    xyz_class: str
    segment_group: str
    annual_revenue: Optional[float] = None
    coefficient_of_variation: Optional[float] = None
    
    class Config:
        from_attributes = True


class OverrideRequest(BaseModel):
    """Request schema for overriding recommendations."""
    override_qty: float = Field(..., gt=0)
    override_reason: str = Field(..., min_length=1)


class MetricsResponse(BaseModel):
    """System metrics response schema."""
    total_skus: int
    total_forecasts: int
    total_recommendations: int
    avg_forecast_accuracy: Optional[float] = None
    stockout_risk_count: int = 0
    overstock_count: int = 0


# --- New Extended Commercial Enterprise Schemas ---

class SKUCreateRequest(BaseModel):
    """Request schema for registering/updating a SKU."""
    sku_id: str = Field(..., min_length=2, max_length=50)
    description: str = Field(..., min_length=2)
    category: str = "Automotive / Components"
    lead_time_days: int = Field(default=90, ge=1)
    unit_cost: float = Field(default=10.0, ge=0.01)
    minimum_order_qty: int = Field(default=50, ge=1)
    supplier_name: Optional[str] = "Global OEM Supplier"


class SKUResponse(BaseModel):
    """Response schema for SKU Master data."""
    sku_id: str
    description: str
    category: str
    lead_time_days: int
    unit_cost: float
    minimum_order_qty: int
    supplier_name: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class SalesRecord(BaseModel):
    """Single historical transaction entry."""
    sku_id: str
    date: date
    quantity: float
    revenue: Optional[float] = None


class SalesImportRequest(BaseModel):
    """Batch ingestion of sales history."""
    records: List[SalesRecord]


class SalesImportResponse(BaseModel):
    status: str
    imported_count: int
    errors: List[str] = Field(default_factory=list)


class ForecastGenerateRequest(BaseModel):
    """Trigger ad-hoc forecasting job."""
    sku_id: Optional[str] = None
    horizon_periods: int = Field(default=12, ge=1, le=60)
    model_type: str = "MovingAverage"


class EvaluationMetricItem(BaseModel):
    sku_id: str
    mae: float
    rmse: float
    mape: float
    wape: float
    sample_size: int


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_percent: int
    created_at: datetime
    message: Optional[str] = None
