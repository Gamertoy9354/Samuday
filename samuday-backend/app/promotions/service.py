import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.promotions.models import SaleEvent, Advertisement
from app.promotions.schemas import SaleEventCreate, AdvertisementCreate

logger = logging.getLogger(__name__)

# Pricing for ad placements (simulated, in paise)
AD_PLACEMENT_PRICING = {
    "hero_banner": 500000,    # ₹5000
    "sidebar": 200000,        # ₹2000
    "category_strip": 100000  # ₹1000
}

async def create_sale_event(db: AsyncSession, seller_id: UUID, payload: SaleEventCreate) -> SaleEvent:
    """Creates a new sale event for a seller."""
    listing_ids_str = json.dumps([str(lid) for lid in payload.listing_ids]) if payload.listing_ids else None
    
    event = SaleEvent(
        seller_id=seller_id,
        title=payload.title,
        description=payload.description,
        banner_image_url=payload.banner_image_url,
        discount_percent=payload.discount_percent,
        start_date=payload.start_date,
        end_date=payload.end_date,
        listing_ids_json=listing_ids_str,
        status="active"
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

async def get_active_sale_events(db: AsyncSession) -> List[SaleEvent]:
    """Returns currently active sale events for homepage display."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(SaleEvent).where(
            and_(
                SaleEvent.status == "active",
                SaleEvent.start_date <= now,
                SaleEvent.end_date >= now
            )
        ).order_by(SaleEvent.created_at.desc()).limit(20)
    )
    return list(result.scalars().all())

async def get_seller_sale_events(db: AsyncSession, seller_id: UUID) -> List[SaleEvent]:
    """Returns all sale events for a specific seller."""
    result = await db.execute(
        select(SaleEvent).where(SaleEvent.seller_id == seller_id).order_by(SaleEvent.created_at.desc())
    )
    return list(result.scalars().all())

async def create_advertisement(db: AsyncSession, seller_id: UUID, payload: AdvertisementCreate) -> Advertisement:
    """Creates a paid advertisement. Deducts wallet balance (simulated offline)."""
    cost = AD_PLACEMENT_PRICING.get(payload.placement, 100000)
    
    # In production: deduct from wallet. For now, just log it.
    logger.info(f"[AD PAYMENT SIM] Seller {seller_id} charged ₹{cost/100:.2f} for {payload.placement} ad")
    
    ad = Advertisement(
        seller_id=seller_id,
        title=payload.title,
        image_url=payload.image_url,
        link_url=payload.link_url,
        placement=payload.placement,
        cost_paise=cost,
        status="active",
        start_date=payload.start_date,
        end_date=payload.end_date
    )
    db.add(ad)
    await db.commit()
    await db.refresh(ad)
    return ad

async def get_active_advertisements(db: AsyncSession, placement: Optional[str] = None) -> List[Advertisement]:
    """Returns active advertisements, optionally filtered by placement."""
    now = datetime.now(timezone.utc)
    query = select(Advertisement).where(
        and_(
            Advertisement.status == "active",
            Advertisement.start_date <= now,
            Advertisement.end_date >= now
        )
    )
    if placement:
        query = query.where(Advertisement.placement == placement)
    
    result = await db.execute(query.order_by(Advertisement.created_at.desc()).limit(20))
    return list(result.scalars().all())

async def record_ad_click(db: AsyncSession, ad_id: UUID) -> bool:
    """Records a click on an advertisement."""
    result = await db.execute(select(Advertisement).where(Advertisement.id == ad_id))
    ad = result.scalars().first()
    if not ad:
        return False
    ad.clicks += 1
    await db.commit()
    return True
