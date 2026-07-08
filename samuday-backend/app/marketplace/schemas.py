from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    pillar: str = Field(..., description="marketplace, sheshop, kisan, etc.")
    icon_url: Optional[str] = None

class CategoryCreate(CategoryBase):
    parent_id: Optional[UUID] = None

class CategoryResponse(CategoryBase):
    id: UUID
    parent_id: Optional[UUID]

    class Config:
        from_attributes = True

class ListingMediaCreate(BaseModel):
    media_url: str
    media_type: str = "image"
    sort_order: int = 0

class ListingMediaResponse(BaseModel):
    id: UUID
    media_url: str
    media_type: str
    sort_order: int

    class Config:
        from_attributes = True

class ListingCreate(BaseModel):
    pillar: str = Field(..., description="marketplace, sheshop, kisan")
    category_id: Optional[UUID] = None
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=5)
    price: int = Field(..., ge=0, description="Price in paise")
    listing_type: str = Field(..., description="sale, rent, service, crop, equipment")
    quantity: int = Field(default=1, ge=1)
    unit: Optional[str] = None
    location_geohash: Optional[str] = None
    media_urls: List[str] = Field(default_factory=list)

class ListingResponse(BaseModel):
    id: UUID
    seller_id: UUID
    pillar: str
    category_id: Optional[UUID]
    title: str
    description: str
    price: int
    listing_type: str
    quantity: int
    unit: Optional[str]
    location_geohash: Optional[str]
    status: str
    created_at: datetime
    media: List[ListingMediaResponse] = []

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    listing_id: UUID
    quantity: int = Field(default=1, ge=1)
    fulfillment_type: str = Field(default="self_pickup")  # self_pickup, seller_delivery, courier

class OrderResponse(BaseModel):
    id: UUID
    buyer_id: UUID
    seller_id: UUID
    listing_id: UUID
    quantity: int
    total_amount: int
    status: str
    fulfillment_type: str
    created_at: datetime

    class Config:
        from_attributes = True

class ReviewCreate(BaseModel):
    order_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: UUID
    order_id: Optional[UUID]
    booking_id: Optional[UUID]
    reviewer_id: UUID
    reviewee_id: UUID
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ChatCreate(BaseModel):
    listing_id: Optional[UUID] = None
    seller_id: UUID

class ChatResponse(BaseModel):
    id: UUID
    listing_id: Optional[UUID]
    buyer_id: UUID
    seller_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)

class ChatMessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    sender_id: UUID
    content: str
    translated_content: Optional[str]
    sent_at: datetime

    class Config:
        from_attributes = True
