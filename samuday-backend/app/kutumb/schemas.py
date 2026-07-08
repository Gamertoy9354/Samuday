from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class FamilyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="e.g. Sharma Family")

class FamilyMemberCreate(BaseModel):
    user_id: Optional[UUID] = Field(None, description="App User ID of the relative, if registered")
    relationship_type: str = Field(..., description="spouse, child, parent, sibling, etc.")
    display_name: str = Field(..., min_length=2, max_length=100)
    visible_phone: bool = Field(default=False)
    visible_kyc: bool = Field(default=False)

class FamilyMemberResponse(BaseModel):
    id: UUID
    family_id: UUID
    user_id: Optional[UUID]
    relationship_type: str
    display_name: str
    visible_phone: bool
    visible_kyc: bool

    class Config:
        from_attributes = True

class FamilyResponse(BaseModel):
    id: UUID
    name: str
    head_id: UUID
    members: List[FamilyMemberResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

class CommunityGroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    group_type: str = Field(..., description="neighborhood, temple, society, etc.")
    description: str = Field(..., min_length=10, max_length=1000)
    location_geohash: str = Field(..., min_length=4, max_length=12)

class CommunityGroupResponse(BaseModel):
    id: UUID
    name: str
    group_type: str
    description: str
    location_geohash: str
    created_by: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True

class MatrimonialProfileCreate(BaseModel):
    gender: str = Field(..., description="male, female, other")
    birth_date: datetime
    religion: str = Field(..., min_length=2, max_length=50)
    caste: Optional[str] = Field(None, max_length=50)
    occupation: str = Field(..., min_length=2, max_length=100)
    education: str = Field(..., min_length=2, max_length=100)
    opt_in_confirmed: bool = Field(..., description="Must explicitly check True to agree to profile creation")

class MatrimonialProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    gender: str
    birth_date: datetime
    religion: str
    caste: Optional[str]
    occupation: str
    education: str
    family_verified_badge: bool
    opt_in_confirmed: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserBlockCreate(BaseModel):
    blocked_user_id: UUID

class UserBlockResponse(BaseModel):
    id: UUID
    user_id: UUID
    blocked_user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class UserReportCreate(BaseModel):
    reported_user_id: UUID
    reason: str = Field(..., min_length=5, max_length=1000)

class UserReportResponse(BaseModel):
    id: UUID
    reporter_id: UUID
    reported_user_id: UUID
    reason: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
