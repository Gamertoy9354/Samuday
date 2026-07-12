from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Literal

# ---------------------------------------------------------------------------
# Family
# ---------------------------------------------------------------------------

class FamilyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="e.g. Sharma Family")

class FamilyMemberCreate(BaseModel):
    user_id: Optional[UUID] = Field(None, description="App User ID of the relative, if registered")
    relationship_type: str = Field(..., description="spouse, child, parent, sibling, etc.")
    display_name: str = Field(..., min_length=2, max_length=100)
    visible_phone: bool = Field(default=False)
    visible_kyc: bool = Field(default=False)

class FamilyMemberVisibilityUpdate(BaseModel):
    visible_phone: Optional[bool] = None
    visible_kyc: Optional[bool] = None

class FamilyInviteRespond(BaseModel):
    accept: bool

class FamilyMemberResponse(BaseModel):
    id: UUID
    family_id: UUID
    user_id: Optional[UUID]
    relationship_type: str
    display_name: str
    visible_phone: bool
    visible_kyc: bool
    status: str
    added_by_user_id: Optional[UUID]
    created_at: datetime

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

# ---------------------------------------------------------------------------
# Community groups
# ---------------------------------------------------------------------------

class CommunityGroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    group_type: str = Field(..., description="neighborhood, temple, society, alumni, other")
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
    member_count: int = 0
    is_member: bool = False

    class Config:
        from_attributes = True

# ---------------------------------------------------------------------------
# Matrimonial
# ---------------------------------------------------------------------------

class MatrimonialOptIn(BaseModel):
    gender: Literal["male", "female", "other"]
    religion: str = Field(..., min_length=2, max_length=50)
    caste: Optional[str] = Field(None, max_length=50)
    occupation: str = Field(..., min_length=2, max_length=100)
    education: str = Field(..., min_length=2, max_length=100)
    about: Optional[str] = Field(None, max_length=1000)
    photo_url: Optional[str] = None
    show_verified_family_badge: bool = Field(default=False)
    consent_confirmed: bool = Field(..., description="Must explicitly be true — the standalone matrimonial consent statement, not the general app ToS")

class MatrimonialProfileUpdate(BaseModel):
    religion: Optional[str] = Field(None, min_length=2, max_length=50)
    caste: Optional[str] = Field(None, max_length=50)
    occupation: Optional[str] = Field(None, min_length=2, max_length=100)
    education: Optional[str] = Field(None, min_length=2, max_length=100)
    about: Optional[str] = Field(None, max_length=1000)
    photo_url: Optional[str] = None
    show_verified_family_badge: Optional[bool] = None
    status: Optional[Literal["active", "paused"]] = None

class MatrimonialProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    gender: str
    age: int
    religion: str
    caste: Optional[str]
    occupation: str
    education: str
    about: Optional[str] = None  # None when hidden from this viewer
    photo_url: Optional[str] = None  # None when hidden from this viewer
    status: str
    age_verified: bool
    family_verified_badge: bool
    show_verified_family_badge: bool
    opt_in_confirmed: bool
    my_interest_status: Optional[str] = None  # none, sent_pending, received_pending, matched, declined — only set in search results
    created_at: datetime

    class Config:
        from_attributes = True

class MatrimonialInterestCreate(BaseModel):
    to_user_id: UUID

class MatrimonialInterestRespond(BaseModel):
    action: Literal["accept", "decline", "withdraw"]

class MatrimonialInterestResponse(BaseModel):
    id: UUID
    from_user_id: UUID
    to_user_id: UUID
    status: str
    created_at: datetime
    responded_at: Optional[datetime]

    class Config:
        from_attributes = True

class MatrimonialInterestWithProfile(BaseModel):
    id: UUID
    from_user_id: UUID
    to_user_id: UUID
    status: str
    created_at: datetime
    responded_at: Optional[datetime]
    counterpart_profile: Optional[MatrimonialProfileResponse] = None

# ---------------------------------------------------------------------------
# Safety: blocking & reporting
# ---------------------------------------------------------------------------

class UserBlockCreate(BaseModel):
    blocked_user_id: UUID

class UserBlockResponse(BaseModel):
    id: UUID
    user_id: UUID
    blocked_user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

ReportReasonCode = Literal["harassment", "fake_profile", "inappropriate_content", "underage_suspicion", "other"]

class UserReportCreate(BaseModel):
    reported_user_id: UUID
    reason_code: ReportReasonCode = "other"
    details: Optional[str] = Field(None, max_length=1000)

class UserReportResponse(BaseModel):
    id: UUID
    reporter_id: UUID
    reported_user_id: UUID
    reason_code: str
    details: Optional[str]
    status: str
    resolved_at: Optional[datetime]
    resolution_action: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------------------------
# Admin moderation
# ---------------------------------------------------------------------------

class AdminReportRow(BaseModel):
    id: UUID
    reporter_id: UUID
    reported_user_id: UUID
    reason_code: str
    details: Optional[str]
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]
    resolution_action: Optional[str]
    reported_profile_status: Optional[str] = None
    reported_profile_age_verified: Optional[bool] = None
    report_count_against_user: int = 0

class AdminReportResolve(BaseModel):
    action: Literal["dismiss", "suspend_profile", "reinstate_profile", "remove_profile"]
    note: Optional[str] = Field(None, max_length=500)
