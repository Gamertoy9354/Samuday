from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class DispatchProfileCreate(BaseModel):
    contact_name: str = Field(..., min_length=2, max_length=100)
    contact_phone: str = Field(..., min_length=10, max_length=15)
    pickup_address_line1: str = Field(..., min_length=3)
    pickup_address_line2: Optional[str] = None
    pickup_city: str = Field(..., min_length=2)
    pickup_state: str = Field(..., min_length=2)
    pickup_pincode: str = Field(..., min_length=6, max_length=6)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class DispatchProfileResponse(DispatchProfileCreate):
    id: UUID
    seller_id: UUID
    delhivery_client_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ShipmentResponse(BaseModel):
    id: UUID
    order_id: UUID
    waybill_number: Optional[str]
    courier_status: str
    tracking_url: Optional[str]
    origin_pincode: str
    destination_pincode: str
    weight_grams: int
    delivery_fee_paise: int
    estimated_delivery_date: Optional[datetime]
    is_simulated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ShippingRateRequest(BaseModel):
    listing_id: UUID
    quantity: int = Field(default=1, ge=1)
    destination_pincode: str = Field(..., min_length=6, max_length=6)

class ShippingRateResponse(BaseModel):
    delivery_fee_paise: int
    is_simulated: bool
