from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class SupplierProfileCreate(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=150)
    gstin: str = Field(..., min_length=15, max_length=15, description="15-character GST Registration Number")

class SupplierProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    business_name: str
    gstin: str
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class SupplierDashboardMetrics(BaseModel):
    total_sales_paise: int = Field(default=0)
    crop_listings_count: int = Field(default=0)
    completed_orders_count: int = Field(default=0)
    active_bookings_count: int = Field(default=0)

class AuditLogResponse(BaseModel):
    id: UUID
    action_type: str
    actor_id: Optional[UUID]
    entity_id: Optional[UUID]
    metadata_json: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
