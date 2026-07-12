from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class AdminSellerRow(BaseModel):
    id: UUID
    full_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    seller_tier: Optional[str] = None
    seller_verification_status: str
    listing_count: int
    created_at: datetime

class AdminListingRow(BaseModel):
    id: UUID
    title: str
    seller_id: UUID
    seller_name: Optional[str] = None
    price: int
    quantity: int
    status: str
    pillar: str
    created_at: datetime

class AdminOverview(BaseModel):
    total_users: int
    total_sellers: int
    official_sellers: int
    local_sellers: int
    pending_verifications: int
    total_listings: int
    active_listings: int
    total_orders: int
    completed_orders: int
    gmv_paise: int  # gross merchandise value — sum of completed order product_amount
    platform_fee_revenue_paise: int
    delivery_fee_collected_paise: int
    platform_house_balance_paise: int
