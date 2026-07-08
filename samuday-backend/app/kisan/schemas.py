from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from app.marketplace.schemas import ListingCreate, ListingResponse, ListingMediaResponse

class CropListingCreate(ListingCreate):
    crop_type: str = Field(..., min_length=2, max_length=100, description="e.g. Wheat, Cotton, Rice")
    grade: str = Field(..., min_length=1, max_length=50, description="e.g. Grade A, FAQ")
    harvest_date: datetime
    mandi_price_reference: Optional[int] = Field(None, ge=0, description="Reference mandi price in paise")

class CropListingResponse(ListingResponse):
    crop_type: str
    grade: str
    harvest_date: datetime
    mandi_price_reference: Optional[int]

    class Config:
        from_attributes = True

class EquipmentListingCreate(ListingCreate):
    equipment_type: str = Field(..., min_length=2, max_length=100, description="e.g. Tractor, Harvester")
    rental_unit: str = Field(..., description="per_hour, per_acre, per_day")
    operator_included: bool = Field(default=False)

class EquipmentListingResponse(ListingResponse):
    equipment_type: str
    rental_unit: str
    operator_included: bool

    class Config:
        from_attributes = True

class LoanApplicationCreate(BaseModel):
    amount_requested: int = Field(..., gt=0, description="Requested amount in paise (100 paise = 1 INR)")
    purpose: str = Field(..., min_length=5, max_length=500, description="Purpose of the loan, e.g. buying seeds")

class LoanApplicationResponse(BaseModel):
    id: UUID
    farmer_id: UUID
    amount_requested: int
    purpose: str
    lender_partner_id: Optional[UUID]
    status: str
    submitted_at: datetime

    class Config:
        from_attributes = True

class AdvisoryChatRequest(BaseModel):
    query_text: str = Field(..., min_length=1, description="Farmer query in English, Hindi, or Gujarati")

class AdvisoryChatResponse(BaseModel):
    query_text: str
    response_text: str
    created_at: datetime

    class Config:
        from_attributes = True
