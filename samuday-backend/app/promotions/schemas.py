from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class SaleEventCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    banner_image_url: Optional[str] = None
    discount_percent: int = Field(default=10, ge=1, le=90)
    start_date: datetime
    end_date: datetime
    listing_ids: List[UUID] = Field(default_factory=list)

class SaleEventResponse(BaseModel):
    id: UUID
    seller_id: UUID
    title: str
    description: Optional[str]
    banner_image_url: Optional[str]
    discount_percent: int
    start_date: datetime
    end_date: datetime
    listing_ids_json: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class AdvertisementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    image_url: str
    link_url: Optional[str] = None
    placement: str = Field(default="hero_banner", description="hero_banner, sidebar, category_strip")
    start_date: datetime
    end_date: datetime

class AdvertisementResponse(BaseModel):
    id: UUID
    seller_id: UUID
    title: str
    image_url: str
    link_url: Optional[str]
    placement: str
    cost_paise: int
    status: str
    start_date: datetime
    end_date: datetime
    impressions: int
    clicks: int
    created_at: datetime

    class Config:
        from_attributes = True
