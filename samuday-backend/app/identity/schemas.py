from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional
import re

class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    preferred_language: str = Field(default="en")

    @field_validator("preferred_language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in ["en", "hi", "gu"]:
            raise ValueError("Language must be one of: en, hi, gu")
        return v

class UserCreate(UserBase):
    phone_number: str = Field(..., description="E.164 phone number, e.g. +919876543210")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Match standard Indian/E.164 phone number format (with + prefix and 10 to 14 digits)
        if not re.match(r"^\+[1-9]\d{10,14}$", v):
            raise ValueError("Phone number must be E.164 format (e.g. +91XXXXXXXXXX)")
        return v

class UserResponse(BaseModel):
    id: UUID
    full_name: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    is_seller: bool = False
    profile_bio: Optional[str] = None
    preferred_language: str = "en"
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    preferred_language: Optional[str] = None
    profile_bio: Optional[str] = Field(None, max_length=500)
    is_seller: Optional[bool] = None

    @field_validator("preferred_language")
    @classmethod
    def validate_lang(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["en", "hi", "gu"]:
            raise ValueError("Language must be one of: en, hi, gu")
        return v

class GoogleAuthRequest(BaseModel):
    """Accepts a Google ID token from the frontend Google Sign-In SDK."""
    credential: str = Field(..., description="Google ID token (JWT) from @react-oauth/google")

class OTPRequest(BaseModel):
    phone_number: str = Field(..., description="E.164 phone number, e.g. +919876543210")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^\+[1-9]\d{10,14}$", v):
            raise ValueError("Phone number must be E.164 format (e.g. +91XXXXXXXXXX)")
        return v

class OTPVerify(BaseModel):
    phone_number: str = Field(..., description="E.164 phone number, e.g. +919876543210")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^\+[1-9]\d{10,14}$", v):
            raise ValueError("Phone number must be E.164 format (e.g. +91XXXXXXXXXX)")
        return v

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class KYCSubmission(BaseModel):
    id_type: str = Field(..., description="aadhaar, pan, voter_id")
    document_url: str = Field(..., description="Secure document URL or storage key reference")

    @field_validator("id_type")
    @classmethod
    def validate_id_type(cls, v: str) -> str:
        if v not in ["aadhaar", "pan", "voter_id"]:
            raise ValueError("ID type must be one of: aadhaar, pan, voter_id")
        return v

class KYCResponse(BaseModel):
    id: UUID
    user_id: UUID
    id_type: str
    document_url: str
    verification_status: str
    created_at: datetime

    class Config:
        from_attributes = True

class VouchCreate(BaseModel):
    vouched_user_id: UUID
    pillar: str = Field(default="general", description="sheshop, kisan, general")

    @field_validator("pillar")
    @classmethod
    def validate_pillar(cls, v: str) -> str:
        if v not in ["sheshop", "kisan", "general"]:
            raise ValueError("Pillar must be one of: sheshop, kisan, general")
        return v

class VouchResponse(BaseModel):
    id: UUID
    voucher_user_id: UUID
    vouched_user_id: UUID
    pillar: str
    created_at: datetime

    class Config:
        from_attributes = True

class ReputationResponse(BaseModel):
    user_id: UUID
    pillar: str
    score: float
    total_transactions: int

    class Config:
        from_attributes = True
