import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.promotions.models import SaleEvent, Advertisement
from app.promotions.schemas import SaleEventCreate, AdvertisementCreate
from app.core.cache import cache_get, cache_set, cache_delete_prefix

logger = logging.getLogger(__name__)

# Pricing for ad placements (simulated, in paise)
AD_PLACEMENT_PRICING = {
    "hero_banner": 500000,    # ₹5000
    "sidebar": 200000,        # ₹2000
    "category_strip": 100000  # ₹1000
}

async def create_sale_event(db: AsyncSession, seller_id: UUID, payload: SaleEventCreate) -> SaleEvent:
    """Creates a new sale event for a seller. Empty listing_ids applies to ALL of the
    seller's listings; overrides lets individual listings use a different discount_percent."""
    listing_ids_str = json.dumps([str(lid) for lid in payload.listing_ids]) if payload.listing_ids else None
    overrides_str = json.dumps(payload.overrides) if payload.overrides else None

    event = SaleEvent(
        seller_id=seller_id,
        title=payload.title,
        description=payload.description,
        banner_image_url=payload.banner_image_url,
        discount_percent=payload.discount_percent,
        start_date=payload.start_date,
        end_date=payload.end_date,
        listing_ids_json=listing_ids_str,
        overrides_json=overrides_str,
        status="active"
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    await cache_delete_prefix("sales:")
    return event

def _sale_event_to_dict(e: SaleEvent) -> dict:
    return {
        "id": str(e.id), "seller_id": str(e.seller_id), "title": e.title, "description": e.description,
        "banner_image_url": e.banner_image_url, "discount_percent": e.discount_percent,
        "start_date": e.start_date.isoformat(), "end_date": e.end_date.isoformat(),
        "listing_ids_json": e.listing_ids_json, "overrides_json": e.overrides_json,
        "status": e.status, "created_at": e.created_at.isoformat(),
    }

async def get_active_sale_events(db: AsyncSession) -> List[dict]:
    """Returns currently active sale events for homepage display. Cached briefly — this is fetched on every homepage load."""
    cache_key = "sales:active"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

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
    events = list(result.scalars().all())
    payload = [_sale_event_to_dict(e) for e in events]
    await cache_set(cache_key, payload, ttl=60)
    return payload

async def get_sale_event_detail(db: AsyncSession, sale_id: UUID) -> Optional[dict]:
    """Returns a sale event plus the listings it applies to, for its public detail page."""
    result = await db.execute(select(SaleEvent).where(SaleEvent.id == sale_id))
    event = result.scalars().first()
    if not event:
        return None

    from app.marketplace import service as market_service
    seller_listings = await market_service.get_seller_public_listings(db, event.seller_id)

    if event.listing_ids_json:
        try:
            target_ids = set(json.loads(event.listing_ids_json))
        except (json.JSONDecodeError, TypeError):
            target_ids = set()
        listings = [l for l in seller_listings if str(l.id) in target_ids]
    else:
        listings = seller_listings

    return {"event": event, "listings": listings}

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
        listing_id=payload.listing_id,
        ai_generated=payload.ai_generated,
        placement=payload.placement,
        cost_paise=cost,
        status="active",
        start_date=payload.start_date,
        end_date=payload.end_date
    )
    db.add(ad)
    await db.commit()
    await db.refresh(ad)
    await cache_delete_prefix("ads:")
    return ad

def _ad_to_dict(a: Advertisement) -> dict:
    return {
        "id": str(a.id), "seller_id": str(a.seller_id), "title": a.title, "image_url": a.image_url,
        "link_url": a.link_url, "listing_id": str(a.listing_id) if a.listing_id else None,
        "ai_generated": a.ai_generated, "placement": a.placement, "cost_paise": a.cost_paise,
        "status": a.status, "start_date": a.start_date.isoformat(), "end_date": a.end_date.isoformat(),
        "impressions": a.impressions, "clicks": a.clicks, "created_at": a.created_at.isoformat(),
    }

async def get_active_advertisements(db: AsyncSession, placement: Optional[str] = None) -> List[dict]:
    """
    Returns active advertisements, optionally filtered by placement. Cached briefly since this
    is fetched on every homepage/search load. Each call also counts as an impression for the
    returned ads (approximate — incremented once per fetch, not per unique viewer — consistent
    with this codebase's other "simulated/approximate" metrics rather than a precise analytics
    pipeline).
    """
    cache_key = f"ads:active:{placement or 'all'}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

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
    ads = list(result.scalars().all())

    if ads:
        ad_ids = [a.id for a in ads]
        await db.execute(
            Advertisement.__table__.update()
            .where(Advertisement.id.in_(ad_ids))
            .values(impressions=Advertisement.impressions + 1)
        )
        await db.commit()
        for a in ads:
            a.impressions += 1

    payload = [_ad_to_dict(a) for a in ads]
    await cache_set(cache_key, payload, ttl=60)
    return payload

async def get_ad_detail(db: AsyncSession, ad_id: UUID) -> Optional[dict]:
    """Returns an advertisement plus its linked listing (if any), for its public detail page."""
    result = await db.execute(select(Advertisement).where(Advertisement.id == ad_id))
    ad = result.scalars().first()
    if not ad:
        return None

    listing = None
    if ad.listing_id:
        from app.marketplace import service as market_service
        listing = await market_service.get_listing_by_id(db, ad.listing_id)

    return {"ad": ad, "listing": listing}

async def get_seller_advertisements(db: AsyncSession, seller_id: UUID) -> List[Advertisement]:
    """Returns all advertisements purchased by a specific seller."""
    result = await db.execute(
        select(Advertisement).where(Advertisement.seller_id == seller_id).order_by(Advertisement.created_at.desc())
    )
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

async def delete_sale_event(db: AsyncSession, seller_id: UUID, sale_id: UUID) -> None:
    """Takes down (deletes) a sale event. Only the owning seller may do this."""
    result = await db.execute(select(SaleEvent).where(SaleEvent.id == sale_id))
    event = result.scalars().first()
    if not event:
        raise ValueError("Sale event not found.")
    if event.seller_id != seller_id:
        raise PermissionError("You do not own this sale event.")
    await db.delete(event)
    await db.commit()
    await cache_delete_prefix("sales:")

async def delete_advertisement(db: AsyncSession, seller_id: UUID, ad_id: UUID) -> None:
    """Takes down (deletes) an advertisement. Only the owning seller may do this."""
    result = await db.execute(select(Advertisement).where(Advertisement.id == ad_id))
    ad = result.scalars().first()
    if not ad:
        raise ValueError("Advertisement not found.")
    if ad.seller_id != seller_id:
        raise PermissionError("You do not own this advertisement.")
    await db.delete(ad)
    await db.commit()
    await cache_delete_prefix("ads:")
