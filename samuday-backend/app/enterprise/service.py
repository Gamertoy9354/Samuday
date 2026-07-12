import json
import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.enterprise.models import SupplierProfile, AuditLog
from app.enterprise.schemas import SupplierProfileCreate, SupplierDashboardMetrics
from app.identity.models import User
from app.marketplace.models import Order, Listing, Booking
from app.kisan.models import CropListing

logger = logging.getLogger(__name__)

async def create_supplier_profile(
    db: AsyncSession,
    user_id: UUID,
    profile_in: SupplierProfileCreate
) -> SupplierProfile:
    """Registers a commercial (Official-tier) supplier business profile for admin review."""
    existing = await get_supplier_profile(db, user_id)
    if existing:
        # Allow re-submission after a rejection
        if existing.verification_status == "rejected":
            existing.business_name = profile_in.business_name
            existing.gstin = profile_in.gstin
            existing.pan = profile_in.pan
            existing.business_phone = profile_in.business_phone
            existing.business_address = profile_in.business_address
            existing.pincode = profile_in.pincode
            existing.verification_status = "pending"
            existing.rejection_reason = None
            await db.commit()
            await db.refresh(existing)
        else:
            return existing
    else:
        existing = SupplierProfile(
            user_id=user_id,
            business_name=profile_in.business_name,
            gstin=profile_in.gstin,
            pan=profile_in.pan,
            business_phone=profile_in.business_phone,
            business_address=profile_in.business_address,
            pincode=profile_in.pincode,
            is_verified=False,
            verification_status="pending",
        )
        db.add(existing)
        await db.commit()
        await db.refresh(existing)

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    if user:
        user.seller_tier = "official"
        user.is_seller = True
        user.seller_verification_status = "pending"
        await db.commit()

    return existing

async def list_pending_supplier_verifications(db: AsyncSession) -> List[SupplierProfile]:
    """Admin: lists pending Official-tier business verifications for review."""
    result = await db.execute(
        select(SupplierProfile).where(SupplierProfile.verification_status == "pending").order_by(SupplierProfile.created_at.asc())
    )
    return list(result.scalars().all())

async def review_supplier_verification(db: AsyncSession, profile_id: UUID, admin_id: UUID, approve: bool, rejection_reason: Optional[str] = None) -> SupplierProfile:
    """Admin: approves or rejects an Official-tier business verification."""
    result = await db.execute(select(SupplierProfile).where(SupplierProfile.id == profile_id))
    profile = result.scalars().first()
    if not profile:
        raise ValueError("Supplier profile not found.")
    if profile.verification_status != "pending":
        raise ValueError("This verification has already been reviewed.")

    profile.verification_status = "approved" if approve else "rejected"
    profile.is_verified = approve
    profile.rejection_reason = None if approve else (rejection_reason or "Not specified")
    profile.verified_at = datetime.now(timezone.utc)
    profile.verified_by = admin_id

    user_result = await db.execute(select(User).where(User.id == profile.user_id))
    user = user_result.scalars().first()
    if user and user.seller_tier == "official":
        user.seller_verification_status = "approved" if approve else "rejected"

    await db.commit()
    await db.refresh(profile)
    return profile

async def get_supplier_profile(db: AsyncSession, user_id: UUID) -> Optional[SupplierProfile]:
    """Retrieves a supplier profile."""
    result = await db.execute(select(SupplierProfile).where(SupplierProfile.user_id == user_id))
    return result.scalars().first()

async def log_audit_action(
    db: AsyncSession,
    action_type: str,
    actor_id: Optional[UUID],
    entity_id: Optional[UUID],
    metadata_dict: Optional[dict] = None
) -> AuditLog:
    """Logs security-critical actions (KYC submissions, wallet credits, credential reviews)."""
    meta_str = json.dumps(metadata_dict) if metadata_dict else None
    
    log = AuditLog(
        action_type=action_type,
        actor_id=actor_id,
        entity_id=entity_id,
        metadata_json=meta_str
    )
    db.add(log)
    await db.flush()  # Use flush so it is written to the db session but committed by the outer transaction
    logger.info(f"[Audit Log] Recorded action: {action_type} by actor {actor_id} on entity {entity_id}")
    return log

async def get_audit_logs(db: AsyncSession) -> List[AuditLog]:
    """Retrieves all transaction and administrative audit logs."""
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()))
    return list(result.scalars().all())

async def get_supplier_dashboard(db: AsyncSession, supplier_user_id: UUID) -> SupplierDashboardMetrics:
    """Aggregates sales volume, crop listings, completed orders, and active bookings for a supplier."""
    # 1. Sum of completed orders' product_amount — what the supplier actually
    # earns. Order.total_amount also includes the platform fee (and delivery fee
    # for courier orders), which the supplier never receives, so using it here
    # would overstate a seller's own sales figure.
    sales_result = await db.execute(
        select(func.sum(Order.product_amount)).where(
            and_(Order.seller_id == supplier_user_id, Order.status == "completed")
        )
    )
    total_sales = sales_result.scalar() or 0

    # 2. Count of completed orders
    orders_result = await db.execute(
        select(func.count(Order.id)).where(
            and_(Order.seller_id == supplier_user_id, Order.status == "completed")
        )
    )
    completed_orders = orders_result.scalar() or 0

    # 3. Count of crop listings joined with marketplace listings
    crops_result = await db.execute(
        select(func.count(CropListing.id))
        .join(Listing, CropListing.listing_id == Listing.id)
        .where(Listing.seller_id == supplier_user_id)
    )
    crop_listings = crops_result.scalar() or 0

    # 4. Count of active bookings
    bookings_result = await db.execute(
        select(func.count(Booking.id)).where(
            and_(
                Booking.provider_id == supplier_user_id,
                Booking.slot_end >= datetime.now(timezone.utc)
            )
        )
    )
    active_bookings = bookings_result.scalar() or 0

    return SupplierDashboardMetrics(
        total_sales_paise=total_sales,
        crop_listings_count=crop_listings,
        completed_orders_count=completed_orders,
        active_bookings_count=active_bookings
    )
