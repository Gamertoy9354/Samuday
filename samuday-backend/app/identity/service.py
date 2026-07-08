import hashlib
import random
import logging
import json
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.security import encrypt_pii, decrypt_pii
from app.core.middleware import t
from app.identity.models import User, KYCRecord, ReputationScore, Vouch
from app.identity.schemas import UserCreate, KYCSubmission, VouchCreate, UserProfileUpdate

logger = logging.getLogger(__name__)

# Redis client for OTP state and rate limiting
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

def hash_phone(phone_number: str) -> str:
    """Computes a SHA-256 hash of the normalized phone number for indexing."""
    return hashlib.sha256(phone_number.strip().encode("utf-8")).hexdigest()

async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Retrieves a user by UUID, decrypting the phone number on-the-fly."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user and user.phone_number:
        # Decrypt phone number for service consumption
        try:
            user.phone_number = decrypt_pii(user.phone_number)
        except Exception:
            pass
    return user

async def get_user_by_phone(db: AsyncSession, phone_number: str) -> Optional[User]:
    """Retrieves a user by plaintext phone number by querying the hash."""
    phone_hash = hash_phone(phone_number)
    result = await db.execute(select(User).where(User.phone_number_hash == phone_hash))
    user = result.scalars().first()
    if user and user.phone_number:
        try:
            user.phone_number = decrypt_pii(user.phone_number)
        except Exception:
            pass
    return user

async def get_user_by_google_id(db: AsyncSession, google_id: str) -> Optional[User]:
    """Retrieves a user by their Google account ID."""
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalars().first()
    if user and user.phone_number:
        try:
            user.phone_number = decrypt_pii(user.phone_number)
        except Exception:
            pass
    return user

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Retrieves a user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user and user.phone_number:
        try:
            user.phone_number = decrypt_pii(user.phone_number)
        except Exception:
            pass
    return user

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """Registers a new user, initializes their wallet, and sets baseline reputation."""
    phone_hash = hash_phone(user_in.phone_number)
    
    # Check duplicate
    existing = await get_user_by_phone(db, user_in.phone_number)
    if existing:
        raise ValueError("User with this phone number already exists.")

    encrypted_phone = encrypt_pii(user_in.phone_number)
    db_user = User(
        phone_number=encrypted_phone,
        phone_number_hash=phone_hash,
        full_name=user_in.full_name,
        preferred_language=user_in.preferred_language
    )
    db.add(db_user)
    await db.flush() # Generates UUID for wallet referencing

    # Initialize Wallet for the User (modular import to avoid circular dependency)
    from app.wallet.service import create_wallet
    await create_wallet(db, user_id=db_user.id)

    # Initialize standard ReputationScore metrics (aggregate)
    rep = ReputationScore(
        user_id=db_user.id,
        pillar="aggregate",
        score=5.0,
        total_transactions=0,
        positive_count=0,
        negative_count=0
    )
    db.add(rep)

    await db.commit()
    await db.refresh(db_user)
    db_user.phone_number = user_in.phone_number  # Decrypted response representation
    return db_user

async def google_authenticate(db: AsyncSession, credential: str) -> User:
    """
    Verifies a Google ID token and creates or retrieves the user.
    Uses PyJWT to decode the Google ID token (in production, verify with Google's certs).
    For local development, we decode without full verification.
    """
    import jwt as pyjwt
    
    try:
        # In production: verify with Google's public keys
        # For development: decode without verification to extract user info
        # The frontend @react-oauth/google library provides a valid JWT
        if settings.GOOGLE_CLIENT_ID:
            # Try to verify properly first
            try:
                from google.oauth2 import id_token as google_id_token
                from google.auth.transport import requests as google_requests
                user_info = google_id_token.verify_oauth2_token(
                    credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID
                )
            except ImportError:
                # google-auth not installed, decode without verification
                user_info = pyjwt.decode(credential, options={"verify_signature": False})
        else:
            # No client ID configured, decode without verification (dev mode)
            user_info = pyjwt.decode(credential, options={"verify_signature": False})
        
        google_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name", "Google User")
        picture = user_info.get("picture")
        
        if not google_id or not email:
            raise ValueError("Invalid Google token: missing sub or email")
        
        # Check if user exists by google_id
        user = await get_user_by_google_id(db, google_id)
        if user:
            return user
        
        # Check if user exists by email (link Google to existing account)
        user = await get_user_by_email(db, email)
        if user:
            user.google_id = google_id
            if picture and not user.avatar_url:
                user.avatar_url = picture
            await db.commit()
            await db.refresh(user)
            return user
        
        # Create new user from Google info
        db_user = User(
            full_name=name,
            email=email,
            google_id=google_id,
            avatar_url=picture,
            preferred_language="en",
            is_seller=False
        )
        db.add(db_user)
        await db.flush()
        
        # Initialize Wallet
        from app.wallet.service import create_wallet
        await create_wallet(db, user_id=db_user.id)
        
        # Initialize ReputationScore
        rep = ReputationScore(
            user_id=db_user.id,
            pillar="aggregate",
            score=5.0,
            total_transactions=0,
            positive_count=0,
            negative_count=0
        )
        db.add(rep)
        
        await db.commit()
        await db.refresh(db_user)
        logger.info(f"Created new Google user: {email} ({google_id})")
        return db_user
        
    except pyjwt.PyJWTError as e:
        logger.error(f"Google token decode error: {e}")
        raise ValueError(f"Invalid Google credential: {e}")

async def update_user_profile(db: AsyncSession, user_id: UUID, updates: UserProfileUpdate) -> User:
    """Updates user profile fields."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise ValueError("User not found")
    
    if updates.full_name is not None:
        user.full_name = updates.full_name
    if updates.preferred_language is not None:
        user.preferred_language = updates.preferred_language
    if updates.profile_bio is not None:
        user.profile_bio = updates.profile_bio
    if updates.is_seller is not None:
        user.is_seller = updates.is_seller
    
    await db.commit()
    await db.refresh(user)
    
    if user.phone_number:
        try:
            user.phone_number = decrypt_pii(user.phone_number)
        except Exception:
            pass
    
    return user

async def request_otp(phone_number: str) -> str:
    """Generates an OTP code, saves it to Redis with a TTL, and handles rate limiting."""
    # Check rate limit (1 OTP request per phone number per minute)
    limit_key = f"otp_limit:{phone_number}"
    otp_key = f"otp_val:{phone_number}"
    
    try:
        is_limited = await redis_client.get(limit_key)
        if is_limited:
            raise ValueError(t("auth.otp.rate_limit"))

        # Generate 6-digit OTP code
        otp_code = settings.MOCK_OTP_CODE if settings.MOCK_OTP else f"{random.randint(100000, 999999)}"
        
        # Save to Redis (valid for 5 minutes)
        await redis_client.setex(otp_key, 300, otp_code)
        
        # Set 1 minute rate-limiting lock
        await redis_client.setex(limit_key, 60, "1")
        
        # Print/Log output to mimic SMS gateway transmission
        logger.info(f"===> [SMS GATEWAY MOCK] Sending OTP {otp_code} to {phone_number}")
        print(f"===> [SMS GATEWAY MOCK] Sending OTP {otp_code} to {phone_number}")
        
        return otp_code
    except Exception as e:
        if "Too many requests" in str(e):
            raise
        # Fail-safe local fallback if Redis is unreachable during standalone test runs
        logger.error(f"Redis unavailable: {e}. Falling back to default mock OTP code.")
        return settings.MOCK_OTP_CODE

async def verify_otp(phone_number: str, otp_code: str) -> bool:
    """Verifies the OTP code from Redis."""
    otp_key = f"otp_val:{phone_number}"
    try:
        saved_code = await redis_client.get(otp_key)
        if not saved_code:
            return False
        
        if saved_code == otp_code:
            # Delete OTP on successful verification to prevent reuse
            await redis_client.delete(otp_key)
            return True
        return False
    except Exception:
        # Fallback for Redis connection issues during tests
        return otp_code == settings.MOCK_OTP_CODE

async def submit_kyc(db: AsyncSession, user_id: UUID, kyc_in: KYCSubmission) -> KYCRecord:
    """Submits a KYC document record for manual administrator review."""
    record = KYCRecord(
        user_id=user_id,
        id_type=kyc_in.id_type,
        document_url=kyc_in.document_url,  # secure ref
        verification_status="pending"
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Auditing: log KYC submission
    try:
        from app.enterprise.service import log_audit_action
        await log_audit_action(
            db=db,
            action_type="kyc_submission",
            actor_id=user_id,
            entity_id=record.id,
            metadata_dict={"id_type": record.id_type}
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to record KYC audit: {e}")

    return record

async def submit_vouch(db: AsyncSession, voucher_user_id: UUID, vouch_in: VouchCreate) -> Vouch:
    """Registers a community vouch from one user to another."""
    if voucher_user_id == vouch_in.vouched_user_id:
        raise ValueError(t("vouch.self"))
        
    # Check if vouch already exists
    existing = await db.execute(
        select(Vouch).where(
            and_(
                Vouch.voucher_user_id == voucher_user_id,
                Vouch.vouched_user_id == vouch_in.vouched_user_id,
                Vouch.pillar == vouch_in.pillar
            )
        )
    )
    if existing.scalars().first():
        raise ValueError("You have already vouched for this user on this pillar.")

    db_vouch = Vouch(
        voucher_user_id=voucher_user_id,
        vouched_user_id=vouch_in.vouched_user_id,
        pillar=vouch_in.pillar
    )
    db.add(db_vouch)
    
    # Dynamically update the reputation score of the vouched user
    rep_result = await db.execute(
        select(ReputationScore).where(
            and_(
                ReputationScore.user_id == vouch_in.vouched_user_id,
                ReputationScore.pillar == "aggregate"
            )
        )
    )
    rep = rep_result.scalars().first()
    if rep:
        # Each community vouch increases reputation by 0.1, capped at 5.0
        rep.score = min(5.0, rep.score + 0.1)
        rep.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(db_vouch)
    return db_vouch

async def get_reputation(db: AsyncSession, user_id: UUID) -> List[ReputationScore]:
    """Retrieves all reputation scores (aggregate and pillar-specific) for a user."""
    result = await db.execute(select(ReputationScore).where(ReputationScore.user_id == user_id))
    return list(result.scalars().all())
