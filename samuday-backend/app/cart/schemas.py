from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class CartItemAdd(BaseModel):
    listing_id: UUID
    quantity: int = Field(default=1, ge=1)

class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1)

class CartItemResponse(BaseModel):
    id: UUID
    user_id: UUID
    listing_id: UUID
    quantity: int
    added_at: datetime
    # Joined listing fields
    listing_title: Optional[str] = None
    listing_price: Optional[int] = None
    listing_image: Optional[str] = None
    seller_id: Optional[UUID] = None

    class Config:
        from_attributes = True

class CartSummaryResponse(BaseModel):
    items: list[CartItemResponse]
    total_items: int
    subtotal_paise: int
