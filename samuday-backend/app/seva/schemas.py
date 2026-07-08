from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class ServiceProviderCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=10, max_length=1000)
    provider_type: str = Field(..., description="Must be 'free', 'subsidized', or 'for_profit'")
    category: str = Field(..., description="e.g. medical, legal, food, education, ngo, general")
    location_geohash: Optional[str] = Field(None, min_length=4, max_length=12)

    class Config:
        from_attributes = True

class ServiceProviderResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str
    provider_type: str
    category: str
    location_geohash: Optional[str]
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ProviderCredentialCreate(BaseModel):
    license_number: str = Field(..., min_length=3, max_length=100, description="Professional certification/license registration number")
    credential_type: str = Field(..., description="medical, legal, NGO, social_work")
    document_url: str = Field(..., min_length=5, description="Link to certificate/document reference")

class ProviderCredentialResponse(BaseModel):
    id: UUID
    provider_id: UUID
    license_number: str  # Decrypted or masked display
    credential_type: str
    document_url: str
    status: str
    verified_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class SevaReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Star rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=1000)
    verified_outcome: Optional[bool] = Field(None, description="Whether this service solved the problem")

class SevaReviewResponse(BaseModel):
    id: UUID
    provider_id: UUID
    reviewer_id: UUID
    rating: int
    comment: Optional[str]
    verified_outcome: Optional[bool]
    created_at: datetime

    class Config:
        from_attributes = True
