from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user, create_access_token, create_refresh_token
from app.core.middleware import t
from app.identity import service
from app.identity.models import User
from app.identity.schemas import (
    OTPRequest, OTPVerify, TokenResponse, UserCreate, UserResponse,
    KYCSubmission, KYCResponse, VouchCreate, VouchResponse, ReputationResponse,
    GoogleAuthRequest, UserProfileUpdate
)

router = APIRouter(prefix="/identity", tags=["Identity & KYC"])

@router.post("/auth/request-otp", status_code=status.HTTP_200_OK)
async def request_otp_endpoint(payload: OTPRequest):
    """Sends OTP to the provided phone number. Mock behavior is guided by settings."""
    try:
        otp_code = await service.request_otp(payload.phone_number)
        return {"message": t("auth.otp.sent"), "mock_otp": otp_code if service.settings.MOCK_OTP else None}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))

@router.post("/auth/verify-otp", response_model=TokenResponse)
async def verify_otp_endpoint(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    """Verifies OTP code and returns access/refresh tokens if registered, or 404 if new user."""
    # Verify OTP
    is_valid = await service.verify_otp(payload.phone_number, payload.otp_code)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=t("auth.otp.invalid"))

    user = await service.get_user_by_phone(db, payload.phone_number)
    if not user:
        # User OTP is verified, but profile doesn't exist. Tell client to register.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REGISTRATION_REQUIRED", "message": "Verify successful, registration required."}
        )

    # Issue tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_endpoint(payload: UserCreate, otp_code: str, db: AsyncSession = Depends(get_db)):
    """Verifies OTP and registers a new user, returning JWT tokens."""
    # Verify OTP
    is_valid = await service.verify_otp(payload.phone_number, otp_code)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=t("auth.otp.invalid"))

    try:
        user = await service.create_user(db, payload)
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/auth/google", response_model=TokenResponse)
async def google_auth_endpoint(payload: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticates via Google ID token. Creates account if new, returns JWT tokens."""
    try:
        user = await service.google_authenticate(db, payload.credential)
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieves current user's decrypted profile."""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_me(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates current user's profile fields."""
    user = await service.update_user_profile(db, current_user.id, payload)
    return user

@router.post("/kyc", response_model=KYCResponse, status_code=status.HTTP_201_CREATED)
async def submit_kyc_endpoint(
    payload: KYCSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submits KYC document links to the trust queue."""
    record = await service.submit_kyc(db, current_user.id, payload)
    return record

@router.post("/vouch", response_model=VouchResponse, status_code=status.HTTP_201_CREATED)
async def submit_vouch_endpoint(
    payload: VouchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Vouches for another user within the community. Reputation updates transactionally."""
    try:
        vouch = await service.submit_vouch(db, current_user.id, payload)
        return vouch
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/reputation", response_model=List[ReputationResponse])
async def get_reputation_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns all reputation records for the current user."""
    scores = await service.get_reputation(db, current_user.id)
    return scores
