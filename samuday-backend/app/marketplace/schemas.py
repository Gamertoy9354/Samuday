from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class AddressCreate(BaseModel):
    label: str = Field(default="Home", max_length=30)
    recipient_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    address_line1: str = Field(..., min_length=3)
    address_line2: Optional[str] = None
    city: str = Field(..., min_length=2)
    state: str = Field(..., min_length=2)
    pincode: str = Field(..., min_length=6, max_length=6)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool = False

class AddressResponse(AddressCreate):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

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
    weight_grams: Optional[int] = Field(None, description="Used for Delhivery shipping rate calculation")
    length_cm: Optional[int] = None
    width_cm: Optional[int] = None
    height_cm: Optional[int] = None
    available_offers: List[str] = Field(default_factory=list)
    return_policy: Optional[str] = None

class ListingResponse(BaseModel):
    id: UUID
    seller_id: UUID
    pillar: str
    category_id: Optional[UUID]
    title: str
    description: str
    weight_grams: Optional[int] = None
    length_cm: Optional[int] = None
    width_cm: Optional[int] = None
    height_cm: Optional[int] = None
    price: int
    listing_type: str
    quantity: int
    unit: Optional[str]
    location_geohash: Optional[str]
    status: str
    created_at: datetime
    media: List[ListingMediaResponse] = []
    available_offers: Optional[List[str]] = None
    return_policy: Optional[str] = None
    rating_avg: Optional[float] = None
    review_count: int = 0
    active_discount_percent: Optional[int] = None

    class Config:
        from_attributes = True

class ListingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = Field(None, min_length=5)
    price: Optional[int] = Field(None, ge=0)
    quantity: Optional[int] = Field(None, ge=0)
    available_offers: Optional[List[str]] = None
    return_policy: Optional[str] = None

class OrderCreate(BaseModel):
    listing_id: UUID
    quantity: int = Field(default=1, ge=1)
    fulfillment_type: str = Field(default="self_pickup")  # self_pickup, seller_delivery, courier
    delivery_address_id: Optional[UUID] = None  # required when fulfillment_type == "courier"

class OrderResponse(BaseModel):
    id: UUID
    buyer_id: UUID
    seller_id: UUID
    listing_id: UUID
    quantity: int
    total_amount: int
    product_amount: int
    platform_fee_amount: int
    delivery_fee_amount: int
    status: str
    fulfillment_type: str
    delivery_address_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True

class OrderDetailResponse(OrderResponse):
    listing_title: Optional[str] = None
    listing_image: Optional[str] = None
    courier_status: Optional[str] = None
    waybill_number: Optional[str] = None
    tracking_url: Optional[str] = None
    is_simulated_shipment: Optional[bool] = None
    has_review: bool = False
    review_id: Optional[UUID] = None
    review_rating: Optional[int] = None
    review_comment: Optional[str] = None

class ReviewCreate(BaseModel):
    order_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: UUID
    order_id: Optional[UUID]
    booking_id: Optional[UUID]
    reviewer_id: UUID
    reviewee_id: UUID
    rating: int
    comment: Optional[str]
    seller_reply: Optional[str] = None
    seller_replied_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ReviewReplyCreate(BaseModel):
    reply: str = Field(..., min_length=1, max_length=2000)

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
