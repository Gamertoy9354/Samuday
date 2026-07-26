import json
import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.middleware import t
from app.core.cache import cache_get, cache_set, cache_delete_prefix
from app.identity.models import User, ReputationScore
from app.marketplace.models import Category, Listing, ListingMedia, Order, Review, Chat, ChatMessage, Address, JobListing, JobApplication, AgriListing
from app.marketplace.schemas import (
    CategoryCreate, ListingCreate, ListingUpdate, OrderCreate, ReviewCreate, AddressCreate,
    JobListingCreate, AgriListingCreate, JobApplicationCreate,
)
from app.marketplace.fees import calculate_order_fees
from app.wallet.service import hold_escrow, release_escrow, refund_escrow
from app.search.service import sync_listing_to_search
from app.ai.service import translate_message, auto_reply_buyer_review
from app.shipping import service as shipping_service

logger = logging.getLogger(__name__)

# --- Category Tree Services ---

async def create_category(db: AsyncSession, cat_in: CategoryCreate) -> Category:
    """
    Creates a new category, or returns the existing one if a category with the same
    name/pillar/parent already exists — this is a check-then-create guard against
    duplicate rows (the DB also carries a unique index as a backstop against races).
    """
    existing = await db.execute(
        select(Category).where(
            and_(
                Category.name == cat_in.name,
                Category.pillar == cat_in.pillar,
                Category.parent_id.is_(cat_in.parent_id) if cat_in.parent_id is None else Category.parent_id == cat_in.parent_id,
            )
        )
    )
    found = existing.scalars().first()
    if found:
        return found

    category = Category(
        parent_id=cat_in.parent_id,
        name=cat_in.name,
        pillar=cat_in.pillar,
        icon_url=cat_in.icon_url
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    await cache_delete_prefix("categories:")
    return category

async def get_categories(db: AsyncSession, pillar: Optional[str] = None) -> List[Category]:
    """Retrieves all categories, optionally filtered by pillar (kisan, sheshop, general). Cached in Redis — the category tree changes rarely but is fetched on every page load."""
    cache_key = f"categories:{pillar or 'all'}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return [Category(**row) for row in cached]

    query = select(Category)
    if pillar:
        query = query.where(Category.pillar == pillar)
    result = await db.execute(query)
    categories = list(result.scalars().all())

    await cache_set(cache_key, [
        {"id": str(c.id), "parent_id": str(c.parent_id) if c.parent_id else None, "name": c.name, "pillar": c.pillar, "icon_url": c.icon_url}
        for c in categories
    ], ttl=300)
    return categories


# --- Listing Services ---

async def create_listing(db: AsyncSession, seller_id: UUID, list_in: ListingCreate) -> Listing:
    """Creates a listing, saves media assets, and registers it with Meilisearch."""
    listing = Listing(
        seller_id=seller_id,
        pillar=list_in.pillar,
        category_id=list_in.category_id,
        title=list_in.title,
        description=list_in.description,
        price=list_in.price,
        listing_type=list_in.listing_type,
        quantity=list_in.quantity,
        unit=list_in.unit,
        location_geohash=list_in.location_geohash,
        weight_grams=list_in.weight_grams,
        length_cm=list_in.length_cm,
        width_cm=list_in.width_cm,
        height_cm=list_in.height_cm,
        available_offers_json=json.dumps(list_in.available_offers) if list_in.available_offers else None,
        return_policy=list_in.return_policy,
        status="active"
    )
    db.add(listing)
    await db.flush()  # Get listing UUID

    # Create media entries
    for idx, url in enumerate(list_in.media_urls):
        media = ListingMedia(
            listing_id=listing.id,
            media_url=url,
            media_type="image",
            sort_order=idx
        )
        db.add(media)

    await db.commit()
    await cache_delete_prefix("listings:")

    # Refresh to load relationships (e.g. media)
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media))
        .where(Listing.id == listing.id)
    )
    db_listing = result.scalars().first()
    
    # Sync with Meilisearch (non-blocking log if search container is not up)
    try:
        await sync_listing_to_search(db_listing)
    except Exception as e:
        logger.error(f"Search sync failed: {e}")

    enriched = await _enrich_listings(db, [db_listing])
    return enriched[0]

async def _enrich_listings(db: AsyncSession, listings: List[Listing]) -> List[Listing]:
    """
    Attaches transient (non-persisted) response fields to each Listing instance:
    - available_offers: parsed from the available_offers_json column
    - rating_avg / review_count: real aggregates from marketplace.reviews (via the
      order that earned the review), replacing the old client-side fake-rating hash
    - active_discount_percent: the best currently-active sale discount that applies
      to this listing (explicit listing_ids match, seller-wide sale, or a per-listing
      override), so the storefront never shows a discount that isn't real
    Batches both aggregates in two queries regardless of list size, then attaches
    the results as plain instance attributes (not mapped columns, so nothing here
    is written back to the DB).
    """
    if not listings:
        return listings

    ids = [l.id for l in listings]
    seller_ids = list({l.seller_id for l in listings})

    rating_map = {}
    rating_rows = await db.execute(
        select(Order.listing_id, func.avg(Review.rating), func.count(Review.id))
        .join(Review, Review.order_id == Order.id)
        .where(Order.listing_id.in_(ids))
        .group_by(Order.listing_id)
    )
    for listing_id, avg_rating, count in rating_rows.all():
        rating_map[listing_id] = (round(float(avg_rating), 1), count)

    # Active sale events for the sellers of these listings
    now = datetime.now(timezone.utc)
    from app.promotions.models import SaleEvent
    sale_rows = await db.execute(
        select(SaleEvent).where(
            and_(
                SaleEvent.seller_id.in_(seller_ids),
                SaleEvent.status == "active",
                SaleEvent.start_date <= now,
                SaleEvent.end_date >= now,
            )
        )
    )
    sales_by_seller: dict = {}
    for sale in sale_rows.scalars().all():
        sales_by_seller.setdefault(sale.seller_id, []).append(sale)

    job_rows = await db.execute(select(JobListing).where(JobListing.listing_id.in_(ids)))
    job_by_listing = {j.listing_id: j for j in job_rows.scalars().all()}
    agri_rows = await db.execute(select(AgriListing).where(AgriListing.listing_id.in_(ids)))
    agri_by_listing = {a.listing_id: a for a in agri_rows.scalars().all()}

    for listing in listings:
        listing.job_details = job_by_listing.get(listing.id)
        listing.agri_details = agri_by_listing.get(listing.id)
        rating_avg, review_count = rating_map.get(listing.id, (None, 0))
        listing.rating_avg = rating_avg
        listing.review_count = review_count

        try:
            listing.available_offers = json.loads(listing.available_offers_json) if listing.available_offers_json else []
        except (json.JSONDecodeError, TypeError):
            listing.available_offers = []

        best_discount = None
        for sale in sales_by_seller.get(listing.seller_id, []):
            applies = True
            discount = sale.discount_percent
            if sale.listing_ids_json:
                try:
                    target_ids = set(json.loads(sale.listing_ids_json))
                except (json.JSONDecodeError, TypeError):
                    target_ids = set()
                applies = str(listing.id) in target_ids
            if applies and sale.overrides_json:
                try:
                    overrides = json.loads(sale.overrides_json)
                    if str(listing.id) in overrides:
                        discount = int(overrides[str(listing.id)])
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
            if applies and (best_discount is None or discount > best_discount):
                best_discount = discount
        listing.active_discount_percent = best_discount

    return listings


async def get_listings(
    db: AsyncSession,
    pillar: Optional[str] = None,
    category_id: Optional[UUID] = None,
    query: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: float = 5.0,
    seller_tier: Optional[str] = None,
) -> List[Listing]:
    """
    Retrieves active listings, with pillar/category/text/seller_tier filters all
    combinable. Reads directly from Postgres (the same table sellers write to via
    create_listing), so results are always consistent with what's actually been
    published — no dependency on a separate search index that can fall out of
    sync or be unavailable.

    The single most common call shape — no filters at all (the homepage's default
    feed) — is cached in Redis for a short TTL, since it's re-fetched on every
    homepage load. Filtered/text-search/geo-radius calls are too varied to cache
    usefully and go straight to Postgres.
    """
    cacheable = not any([pillar, category_id, query, lat, lng, seller_tier])
    cache_key = "listings:feed:all"
    if cacheable:
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

    db_query = (
        select(Listing)
        .options(selectinload(Listing.media), selectinload(Listing.category))
        .where(Listing.status == "active")
    )
    if pillar:
        db_query = db_query.where(Listing.pillar == pillar)
    if category_id:
        db_query = db_query.where(Listing.category_id == category_id)
    if seller_tier:
        db_query = db_query.where(Listing.seller_id.in_(select(User.id).where(User.seller_tier == seller_tier)))

    if query and query.strip():
        for term in query.strip().split():
            like = f"%{term}%"
            db_query = db_query.where(
                or_(
                    Listing.title.ilike(like),
                    Listing.description.ilike(like),
                    Listing.category.has(Category.name.ilike(like))
                )
            )

    db_query = db_query.order_by(Listing.created_at.desc())

    result = await db.execute(db_query)
    listings = list(result.scalars().all())
    enriched = await _enrich_listings(db, listings)

    if cacheable:
        await cache_set(cache_key, [_listing_to_cache_dict(l) for l in enriched], ttl=45)
    return enriched

def _listing_to_cache_dict(l: Listing) -> dict:
    """Serializes an enriched Listing (with its transient _enrich_listings attributes) to a plain dict for Redis caching. FastAPI validates dicts against ListingResponse the same as ORM objects."""
    return {
        "id": str(l.id), "seller_id": str(l.seller_id), "pillar": l.pillar,
        "category_id": str(l.category_id) if l.category_id else None,
        "title": l.title, "description": l.description,
        "weight_grams": l.weight_grams, "length_cm": l.length_cm, "width_cm": l.width_cm, "height_cm": l.height_cm,
        "price": l.price, "listing_type": l.listing_type, "quantity": l.quantity, "unit": l.unit,
        "location_geohash": l.location_geohash, "status": l.status,
        "created_at": l.created_at.isoformat() if l.created_at else None,
        "media": [{"id": str(m.id), "media_url": m.media_url, "media_type": m.media_type, "sort_order": m.sort_order} for m in l.media],
        "available_offers": getattr(l, "available_offers", None),
        "return_policy": l.return_policy,
        "rating_avg": getattr(l, "rating_avg", None),
        "review_count": getattr(l, "review_count", 0),
        "active_discount_percent": getattr(l, "active_discount_percent", None),
        "job_details": _job_details_to_dict(getattr(l, "job_details", None)),
        "agri_details": _agri_details_to_dict(getattr(l, "agri_details", None)),
    }

def _job_details_to_dict(j) -> Optional[dict]:
    if not j:
        return None
    return {
        "job_type": j.job_type, "salary_min": j.salary_min, "salary_max": j.salary_max,
        "salary_period": j.salary_period, "experience_required": j.experience_required,
        "openings": j.openings,
        "application_deadline": j.application_deadline.isoformat() if j.application_deadline else None,
        "contact_email": j.contact_email,
    }

def _agri_details_to_dict(a) -> Optional[dict]:
    if not a:
        return None
    return {
        "crop_type": a.crop_type, "is_organic": a.is_organic,
        "harvest_date": a.harvest_date.isoformat() if a.harvest_date else None,
        "grade": a.grade,
    }

async def get_seller_public_profile(db: AsyncSession, seller_id: UUID) -> Optional[dict]:
    """Returns a seller's public storefront info (name, avatar, tier, reputation), for their public seller page."""
    user_result = await db.execute(select(User).where(User.id == seller_id))
    user = user_result.scalars().first()
    if not user or not user.is_seller:
        return None

    rep_result = await db.execute(
        select(ReputationScore).where(and_(ReputationScore.user_id == seller_id, ReputationScore.pillar == "aggregate"))
    )
    rep = rep_result.scalars().first()

    listing_count = await db.scalar(
        select(func.count(Listing.id)).where(and_(Listing.seller_id == seller_id, Listing.status == "active"))
    )

    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "profile_bio": user.profile_bio,
        "seller_tier": user.seller_tier,
        "seller_verification_status": user.seller_verification_status,
        "member_since": user.created_at.isoformat() if user.created_at else None,
        "rating": round(rep.score, 1) if rep else None,
        "total_transactions": rep.total_transactions if rep else 0,
        "active_listing_count": listing_count or 0,
    }

async def get_seller_public_listings(db: AsyncSession, seller_id: UUID) -> List[Listing]:
    """Returns a seller's active listings, for their public storefront page."""
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media), selectinload(Listing.category))
        .where(and_(Listing.seller_id == seller_id, Listing.status == "active"))
        .order_by(Listing.created_at.desc())
    )
    listings = list(result.scalars().all())
    return await _enrich_listings(db, listings)

async def get_all_listings(db: AsyncSession, limit: int = 50) -> List[Listing]:
    """Retrieves the most recently published active listings with media and category preloaded."""
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media), selectinload(Listing.category))
        .where(Listing.status == "active")
        .order_by(Listing.created_at.desc())
        .limit(limit)
    )
    listings = list(result.scalars().all())
    return await _enrich_listings(db, listings)

async def get_listing_by_id(db: AsyncSession, listing_id: UUID) -> Optional[Listing]:
    """Retrieves a listing by UUID."""
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media))
        .where(Listing.id == listing_id)
    )
    listing = result.scalars().first()
    if not listing:
        return None
    enriched = await _enrich_listings(db, [listing])
    return enriched[0]

async def get_my_listings(db: AsyncSession, seller_id: UUID) -> List[Listing]:
    """Returns all of a seller's own listings regardless of status (active, paused, removed, sold), for their dashboard."""
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media), selectinload(Listing.category))
        .where(Listing.seller_id == seller_id)
        .order_by(Listing.created_at.desc())
    )
    listings = list(result.scalars().all())
    return await _enrich_listings(db, listings)

async def _get_owned_listing(db: AsyncSession, seller_id: UUID, listing_id: UUID) -> Listing:
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalars().first()
    if not listing:
        raise ValueError(t("listing.not_found"))
    if listing.seller_id != seller_id:
        raise PermissionError("You do not own this listing.")
    return listing

async def _reload_with_media(db: AsyncSession, listing_id: UUID) -> Listing:
    """Re-fetches a listing with media eager-loaded, needed before returning it as a ListingResponse (media is lazy by default and can't be awaited after commit)."""
    result = await db.execute(
        select(Listing).options(selectinload(Listing.media)).where(Listing.id == listing_id)
    )
    return result.scalars().first()

async def pause_listing(db: AsyncSession, seller_id: UUID, listing_id: UUID) -> Listing:
    """Temporarily takes a listing down from public view (buyers can no longer find or order it). Reversible via reactivate_listing."""
    listing = await _get_owned_listing(db, seller_id, listing_id)
    if listing.status != "active":
        raise ValueError("Only active listings can be paused.")
    listing.status = "paused"
    await db.commit()
    await cache_delete_prefix("listings:")
    db_listing = await _reload_with_media(db, listing_id)
    try:
        await sync_listing_to_search(db_listing)
    except Exception as e:
        logger.error(f"Search sync failed: {e}")
    enriched = await _enrich_listings(db, [db_listing])
    return enriched[0]

async def reactivate_listing(db: AsyncSession, seller_id: UUID, listing_id: UUID) -> Listing:
    """Brings a temporarily paused listing back to public view."""
    listing = await _get_owned_listing(db, seller_id, listing_id)
    if listing.status != "paused":
        raise ValueError("Only paused listings can be reactivated.")
    listing.status = "active"
    await db.commit()
    await cache_delete_prefix("listings:")
    db_listing = await _reload_with_media(db, listing_id)
    try:
        await sync_listing_to_search(db_listing)
    except Exception as e:
        logger.error(f"Search sync failed: {e}")
    enriched = await _enrich_listings(db, [db_listing])
    return enriched[0]

async def remove_listing_permanently(db: AsyncSession, seller_id: UUID, listing_id: UUID) -> Listing:
    """
    Permanently takes a listing down. This is a soft delete (status='removed', row kept)
    rather than a hard DELETE, since past orders reference this listing (Order.listing_id
    is ondelete=RESTRICT) and must keep working in order history. Not reversible via the API.
    """
    listing = await _get_owned_listing(db, seller_id, listing_id)
    if listing.status == "removed":
        raise ValueError("Listing is already removed.")
    listing.status = "removed"
    await db.commit()
    await cache_delete_prefix("listings:")
    db_listing = await _reload_with_media(db, listing_id)
    try:
        await sync_listing_to_search(db_listing)
    except Exception as e:
        logger.error(f"Search sync failed: {e}")
    enriched = await _enrich_listings(db, [db_listing])
    return enriched[0]

async def update_listing(db: AsyncSession, seller_id: UUID, listing_id: UUID, updates: "ListingUpdate") -> Listing:
    """Seller updates their own listing's editable fields (price, description, offers, return policy, etc.)."""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalars().first()
    if not listing:
        raise ValueError(t("listing.not_found"))
    if listing.seller_id != seller_id:
        raise PermissionError("You do not own this listing.")

    if updates.title is not None:
        listing.title = updates.title
    if updates.description is not None:
        listing.description = updates.description
    if updates.price is not None:
        listing.price = updates.price
    if updates.quantity is not None:
        listing.quantity = updates.quantity
    if updates.available_offers is not None:
        listing.available_offers_json = json.dumps(updates.available_offers) if updates.available_offers else None
    if updates.return_policy is not None:
        listing.return_policy = updates.return_policy

    await db.commit()
    await cache_delete_prefix("listings:")

    result = await db.execute(
        select(Listing).options(selectinload(Listing.media)).where(Listing.id == listing_id)
    )
    db_listing = result.scalars().first()
    try:
        await sync_listing_to_search(db_listing)
    except Exception as e:
        logger.error(f"Search sync failed: {e}")
    enriched = await _enrich_listings(db, [db_listing])
    return enriched[0]


# --- Jobs & Agriculture Listing Extensions ---

async def create_job_listing(db: AsyncSession, seller_id: UUID, job_in: JobListingCreate) -> Listing:
    """
    Creates a Jobs-category listing plus its JobListing extension row (salary, job type,
    application details) in one flow. Reuses create_listing for the shared columns — the
    listing's price is derived from salary_min/salary_max since Jobs postings don't have
    a buyable price, and listing_type is forced to "job" so the buy/cart flow can be
    guarded against it (buyers apply instead, see apply_to_job).
    """
    effective_price = job_in.salary_min if job_in.salary_min is not None else (job_in.salary_max or 0)
    base_in = ListingCreate(
        pillar=job_in.pillar,
        category_id=job_in.category_id,
        title=job_in.title,
        description=job_in.description,
        price=effective_price,
        listing_type="job",
        quantity=job_in.quantity,
        unit=None,
        location_geohash=job_in.location_geohash,
        media_urls=job_in.media_urls,
    )
    listing = await create_listing(db, seller_id, base_in)

    db.add(JobListing(
        listing_id=listing.id,
        job_type=job_in.job_type,
        salary_min=job_in.salary_min,
        salary_max=job_in.salary_max,
        salary_period=job_in.salary_period,
        experience_required=job_in.experience_required,
        openings=job_in.quantity,
        application_deadline=job_in.application_deadline,
        contact_email=job_in.contact_email,
    ))
    await db.commit()

    return await get_listing_by_id(db, listing.id)

async def create_agri_listing(db: AsyncSession, seller_id: UUID, agri_in: AgriListingCreate) -> Listing:
    """Creates an Agriculture-category listing plus its AgriListing extension row (crop type, unit-based price, organic/harvest/grade)."""
    base_in = ListingCreate(
        pillar=agri_in.pillar,
        category_id=agri_in.category_id,
        title=agri_in.title,
        description=agri_in.description,
        price=agri_in.price,
        listing_type="crop",
        quantity=agri_in.quantity,
        unit=agri_in.unit,
        location_geohash=agri_in.location_geohash,
        media_urls=agri_in.media_urls,
        weight_grams=agri_in.weight_grams,
        length_cm=agri_in.length_cm,
        width_cm=agri_in.width_cm,
        height_cm=agri_in.height_cm,
        available_offers=agri_in.available_offers,
        return_policy=agri_in.return_policy,
    )
    listing = await create_listing(db, seller_id, base_in)

    db.add(AgriListing(
        listing_id=listing.id,
        crop_type=agri_in.crop_type,
        is_organic=agri_in.is_organic,
        harvest_date=agri_in.harvest_date,
        grade=agri_in.grade,
    ))
    await db.commit()

    return await get_listing_by_id(db, listing.id)

async def apply_to_job(db: AsyncSession, listing_id: UUID, applicant_id: UUID, payload: JobApplicationCreate) -> JobApplication:
    """Submits a buyer's application to a Jobs listing — the Jobs-flow equivalent of placing an order."""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalars().first()
    if not listing:
        raise ValueError(t("listing.not_found"))
    if listing.seller_id == applicant_id:
        raise ValueError("You cannot apply to your own job listing.")

    job_result = await db.execute(select(JobListing).where(JobListing.listing_id == listing_id))
    if not job_result.scalars().first():
        raise ValueError("This listing is not a job posting.")

    existing = await db.execute(
        select(JobApplication).where(
            and_(JobApplication.listing_id == listing_id, JobApplication.applicant_id == applicant_id)
        )
    )
    if existing.scalars().first():
        raise ValueError("You have already applied to this job.")

    application = JobApplication(listing_id=listing_id, applicant_id=applicant_id, message=payload.message)
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application

async def get_job_applications(db: AsyncSession, seller_id: UUID, listing_id: UUID) -> List[dict]:
    """Seller-only: returns everyone who applied to one of their job listings, most recent first."""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalars().first()
    if not listing:
        raise ValueError(t("listing.not_found"))
    if listing.seller_id != seller_id:
        raise PermissionError("You do not own this listing.")

    from app.identity.service import get_user_by_id

    rows = (await db.execute(
        select(JobApplication).where(JobApplication.listing_id == listing_id).order_by(JobApplication.applied_at.desc())
    )).scalars().all()

    applicants = []
    for app in rows:
        user = await get_user_by_id(db, app.applicant_id)
        applicants.append({
            "id": app.id, "listing_id": app.listing_id, "applicant_id": app.applicant_id,
            "applicant_name": user.full_name if user else None,
            "applicant_phone": user.phone_number if user else None,
            "listing_title": listing.title,
            "message": app.message, "status": app.status, "applied_at": app.applied_at,
        })
    return applicants

async def get_my_applications(db: AsyncSession, applicant_id: UUID) -> List[dict]:
    """Buyer-side: the jobs the current user has applied to, most recent first."""
    result = await db.execute(
        select(JobApplication, Listing.title)
        .join(Listing, Listing.id == JobApplication.listing_id)
        .where(JobApplication.applicant_id == applicant_id)
        .order_by(JobApplication.applied_at.desc())
    )
    return [
        {
            "id": app.id, "listing_id": app.listing_id, "applicant_id": app.applicant_id,
            "listing_title": title, "message": app.message, "status": app.status, "applied_at": app.applied_at,
        }
        for app, title in result.all()
    ]


# --- Order & Escrow Services ---

async def create_order(db: AsyncSession, buyer_id: UUID, order_in: OrderCreate) -> Order:
    """
    Creates an order, calculates platform + delivery fees, places the buyer's
    funds in an escrow hold, and (for courier fulfillment) manifests a shipment.
    Fails if buyer balance is insufficient.
    """
    # Row-lock the listing for the duration of the transaction so two concurrent
    # buyers can't both pass the stock check against the same remaining quantity.
    result = await db.execute(
        select(Listing).where(Listing.id == order_in.listing_id).with_for_update()
    )
    listing = result.scalars().first()
    if not listing:
        raise ValueError(t("listing.not_found"))
    if listing.status != "active":
        raise ValueError("Listing is no longer active.")
    if listing.seller_id == buyer_id:
        raise ValueError("You cannot purchase your own listing.")
    if listing.quantity < order_in.quantity:
        raise ValueError("Requested quantity exceeds available stock.")
    job_check = await db.execute(select(JobListing.id).where(JobListing.listing_id == listing.id))
    if job_check.scalar():
        raise ValueError("This is a job listing — use Apply instead of Buy.")

    product_amount = listing.price * order_in.quantity
    fees = calculate_order_fees(product_amount)
    platform_fee_amount = fees["platform_fee_amount"]
    gateway_fee_estimate = fees["gateway_fee_estimate"]
    delivery_fee_amount = 0
    delivery_address_id = None

    if order_in.fulfillment_type == "courier":
        if not order_in.delivery_address_id:
            raise ValueError("A delivery address is required for courier fulfillment.")
        addr_result = await db.execute(
            select(Address).where(and_(Address.id == order_in.delivery_address_id, Address.user_id == buyer_id))
        )
        address = addr_result.scalars().first()
        if not address:
            raise ValueError("Delivery address not found.")

        dispatch_profile = await shipping_service.get_dispatch_profile(db, listing.seller_id)
        if not dispatch_profile:
            raise ValueError("This seller hasn't set up pickup/dispatch information yet, so courier delivery isn't available for this listing.")

        weight_grams = (listing.weight_grams or shipping_service.DEFAULT_ITEM_WEIGHT_GRAMS) * order_in.quantity
        rate = await shipping_service.calculate_delivery_fee(weight_grams, dispatch_profile.pickup_pincode, address.pincode)
        delivery_fee_amount = rate["amount_paise"]
        delivery_address_id = address.id

    total_amount = product_amount + platform_fee_amount + delivery_fee_amount
    listing.quantity -= order_in.quantity

    order = Order(
        buyer_id=buyer_id,
        seller_id=listing.seller_id,
        listing_id=listing.id,
        quantity=order_in.quantity,
        total_amount=total_amount,
        product_amount=product_amount,
        platform_fee_amount=platform_fee_amount,
        delivery_fee_amount=delivery_fee_amount,
        gateway_fee_estimate=gateway_fee_estimate,
        status="pending",
        fulfillment_type=order_in.fulfillment_type,
        delivery_address_id=delivery_address_id,
    )
    db.add(order)
    await db.flush()  # Generate order UUID

    # Deduct funds and record an escrow hold (rolls back transaction on failure)
    await hold_escrow(db, buyer_id, total_amount, order.id)

    if order_in.fulfillment_type == "courier":
        seller_result = await db.execute(select(User).where(User.id == listing.seller_id))
        seller = seller_result.scalars().first()
        await shipping_service.create_order_shipment(
            db,
            order_id=order.id,
            dispatch_profile=dispatch_profile,
            destination_pincode=address.pincode,
            consignee={
                "name": address.recipient_name,
                "address": address.address_line1,
                "city": address.city,
                "state": address.state,
                "pincode": address.pincode,
                "phone": address.phone,
            },
            weight_grams=weight_grams,
            delivery_fee_paise=delivery_fee_amount,
            total_amount_paise=total_amount,
        )

    order.status = "paid"  # Status changes from pending to paid since funds are escrow-secured
    await db.commit()
    await db.refresh(order)
    return order

async def complete_order(db: AsyncSession, order_id: UUID, current_user_id: UUID) -> Order:
    """Completes an order, releases escrow holds (split between seller and platform), and updates transaction counts."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise ValueError(t("order.not_found"))

    # Only buyer can confirm fulfillment/completion of order
    if order.buyer_id != current_user_id:
        raise ValueError("Only the buyer can mark the order completed.")

    if order.status != "paid":
        raise ValueError("Order must be in paid status to complete.")

    # Release escrow holds (credits seller with product_amount, platform house
    # wallet with platform_fee_amount + delivery_fee_amount)
    await release_escrow(db, order.id, order.seller_id, order.platform_fee_amount, order.delivery_fee_amount)
    order.status = "completed"
    
    # Dynamically update seller and buyer transaction counts in reputation
    for user_id in [order.seller_id, order.buyer_id]:
        rep_result = await db.execute(
            select(ReputationScore).where(
                and_(ReputationScore.user_id == user_id, ReputationScore.pillar == "aggregate")
            )
        )
        rep = rep_result.scalars().first()
        if rep:
            rep.total_transactions += 1
            rep.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(order)
    return order

async def cancel_order(db: AsyncSession, order_id: UUID, current_user_id: UUID) -> Order:
    """Cancels a paid order and refunds the escrowed funds to the buyer."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise ValueError(t("order.not_found"))

    # Either buyer or seller can cancel before completion
    if current_user_id not in [order.buyer_id, order.seller_id]:
        raise ValueError("Unauthorized to cancel this order.")

    if order.status not in ["pending", "paid"]:
        raise ValueError("Order cannot be cancelled in its current state.")

    # Refund escrow holds (credits buyer)
    await refund_escrow(db, order.id, order.buyer_id)
    order.status = "cancelled"

    # Restore the stock that was deducted at order creation time
    listing = await get_listing_by_id(db, order.listing_id)
    if listing:
        listing.quantity += order.quantity

    # Mark any manifested shipment as cancelled too (real Delhivery cancellation
    # would need its own API call once a real account is connected)
    shipment = await shipping_service.get_shipment_for_order(db, order.id)
    if shipment:
        shipment.courier_status = "cancelled"

    await db.commit()
    await db.refresh(order)
    return order


async def get_orders_for_user(db: AsyncSession, user_id: UUID, role: str = "buyer") -> List[dict]:
    """Returns orders for a user (as buyer or seller), enriched with listing/shipment info for display."""
    from app.shipping.models import Shipment

    column = Order.seller_id if role == "seller" else Order.buyer_id
    result = await db.execute(
        select(Order)
        .where(column == user_id)
        .order_by(Order.created_at.desc())
    )
    orders = list(result.scalars().all())
    if not orders:
        return []

    listing_ids = list({o.listing_id for o in orders})
    listings_result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media))
        .where(Listing.id.in_(listing_ids))
    )
    listings_by_id = {l.id: l for l in listings_result.scalars().all()}

    order_ids = [o.id for o in orders]
    shipments_result = await db.execute(select(Shipment).where(Shipment.order_id.in_(order_ids)))
    shipments_by_order = {s.order_id: s for s in shipments_result.scalars().all()}

    reviewed_result = await db.execute(
        select(Review).where(and_(Review.order_id.in_(order_ids), Review.reviewer_id == user_id))
    )
    reviews_by_order = {r.order_id: r for r in reviewed_result.scalars().all()}

    enriched = []
    for o in orders:
        listing = listings_by_id.get(o.listing_id)
        shipment = shipments_by_order.get(o.id)
        review = reviews_by_order.get(o.id)
        enriched.append({
            "id": o.id,
            "buyer_id": o.buyer_id,
            "seller_id": o.seller_id,
            "listing_id": o.listing_id,
            "quantity": o.quantity,
            "total_amount": o.total_amount,
            "product_amount": o.product_amount,
            "platform_fee_amount": o.platform_fee_amount,
            "delivery_fee_amount": o.delivery_fee_amount,
            "status": o.status,
            "fulfillment_type": o.fulfillment_type,
            "delivery_address_id": o.delivery_address_id,
            "created_at": o.created_at,
            "listing_title": listing.title if listing else None,
            "listing_image": listing.media[0].media_url if listing and listing.media else None,
            "courier_status": shipment.courier_status if shipment else None,
            "waybill_number": shipment.waybill_number if shipment else None,
            "tracking_url": shipment.tracking_url if shipment else None,
            "is_simulated_shipment": shipment.is_simulated if shipment else None,
            "has_review": review is not None,
            "review_id": review.id if review else None,
            "review_rating": review.rating if review else None,
            "review_comment": review.comment if review else None,
        })
    return enriched


# --- Address Book Services ---

async def get_addresses(db: AsyncSession, user_id: UUID) -> List[Address]:
    """Returns a user's saved addresses, default first."""
    result = await db.execute(
        select(Address).where(Address.user_id == user_id).order_by(Address.is_default.desc(), Address.created_at.desc())
    )
    return list(result.scalars().all())

async def create_address(db: AsyncSession, user_id: UUID, payload: AddressCreate) -> Address:
    """Saves a new delivery address. If marked default, unsets any previous default."""
    if payload.is_default:
        existing_defaults = (await db.execute(
            select(Address).where(and_(Address.user_id == user_id, Address.is_default == True))  # noqa: E712
        )).scalars().all()
        for addr in existing_defaults:
            addr.is_default = False

    address = Address(user_id=user_id, **payload.model_dump())
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address

async def delete_address(db: AsyncSession, user_id: UUID, address_id: UUID) -> bool:
    result = await db.execute(select(Address).where(and_(Address.id == address_id, Address.user_id == user_id)))
    address = result.scalars().first()
    if not address:
        return False
    await db.delete(address)
    await db.commit()
    return True


# --- Review & Peer Rating Services ---

async def _recompute_reputation(db: AsyncSession, reviewee_id: UUID) -> None:
    """Recalculates a user's aggregate reputation score/counts from their current real reviews. Called after any review is created, edited, or deleted."""
    scores_query = select(func.avg(Review.rating), func.count(Review.id)).where(Review.reviewee_id == reviewee_id)
    score_res = await db.execute(scores_query)
    avg_rating, count = score_res.first()

    rep_result = await db.execute(
        select(ReputationScore).where(
            and_(ReputationScore.user_id == reviewee_id, ReputationScore.pillar == "aggregate")
        )
    )
    rep = rep_result.scalars().first()
    if rep:
        rep.score = float(avg_rating) if avg_rating is not None else 5.0
        rep.positive_count = await db.scalar(
            select(func.count(Review.id)).where(
                and_(Review.reviewee_id == reviewee_id, Review.rating >= 4)
            )
        )
        rep.negative_count = await db.scalar(
            select(func.count(Review.id)).where(
                and_(Review.reviewee_id == reviewee_id, Review.rating <= 2)
            )
        )
        rep.updated_at = datetime.now(timezone.utc)

async def _auto_generate_seller_reply(db: AsyncSession, review: Review) -> None:
    """
    Autonomously drafts and saves an AI reply to a review — no seller action required.
    Called right after a review is submitted or edited, so a reply always appears without
    the seller having to click anything (they can still edit it afterward from the dashboard).
    """
    if not review.order_id:
        return
    result = await db.execute(
        select(User.full_name, Listing.title)
        .select_from(Order)
        .join(Listing, Order.listing_id == Listing.id)
        .join(User, User.id == review.reviewer_id)
        .where(Order.id == review.order_id)
    )
    row = result.first()
    if not row:
        return
    buyer_name, product_title = row
    try:
        reply_text = await auto_reply_buyer_review(buyer_name, review.rating, review.comment or "", product_title)
        review.seller_reply = reply_text
        review.seller_replied_at = datetime.now(timezone.utc)
    except Exception as e:
        logger.error(f"Autonomous AI review reply failed for review {review.id}: {e}")

async def submit_review(db: AsyncSession, reviewer_id: UUID, rev_in: ReviewCreate) -> Review:
    """Submits a rating and comment, updates the reviewee's reputation, and autonomously posts an AI-drafted seller reply."""
    if not rev_in.order_id and not rev_in.booking_id:
        raise ValueError("Review must be linked to an order or booking.")

    # Fetch order to determine reviewee
    order = None
    if rev_in.order_id:
        res = await db.execute(select(Order).where(Order.id == rev_in.order_id))
        order = res.scalars().first()
        if not order:
            raise ValueError(t("order.not_found"))
        if order.status != "completed":
            raise ValueError("You can only review completed orders.")
        if reviewer_id not in [order.buyer_id, order.seller_id]:
            raise ValueError("Unauthorized to review this order.")

        # Reviewee is the other party in the transaction
        reviewee_id = order.seller_id if reviewer_id == order.buyer_id else order.buyer_id

        existing = await db.execute(
            select(Review).where(and_(Review.order_id == order.id, Review.reviewer_id == reviewer_id))
        )
        if existing.scalars().first():
            raise ValueError("You have already reviewed this order.")

    review = Review(
        order_id=rev_in.order_id,
        booking_id=rev_in.booking_id,
        reviewer_id=reviewer_id,
        reviewee_id=reviewee_id,
        rating=rev_in.rating,
        comment=rev_in.comment
    )
    db.add(review)
    await db.flush()  # Generate review UUID

    await _recompute_reputation(db, reviewee_id)
    await _auto_generate_seller_reply(db, review)

    await db.commit()
    await db.refresh(review)
    return review

async def update_review(db: AsyncSession, reviewer_id: UUID, review_id: UUID, rating: Optional[int], comment: Optional[str]) -> Review:
    """
    Lets a buyer edit their own review's rating/comment. Recomputes the seller's reputation
    (since the rating may have changed) and has the AI draft a fresh reply to replace the old
    one, since a reply written for the old rating/comment may no longer make sense.
    """
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalars().first()
    if not review:
        raise ValueError("Review not found.")
    if review.reviewer_id != reviewer_id:
        raise PermissionError("You can only edit your own review.")

    if rating is not None:
        review.rating = rating
    if comment is not None:
        review.comment = comment
    review.seller_reply = None
    review.seller_replied_at = None

    await _recompute_reputation(db, review.reviewee_id)
    await _auto_generate_seller_reply(db, review)

    await db.commit()
    await db.refresh(review)
    return review

async def delete_review(db: AsyncSession, reviewer_id: UUID, review_id: UUID) -> None:
    """Lets a buyer delete their own review, recomputing the seller's reputation afterward."""
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalars().first()
    if not review:
        raise ValueError("Review not found.")
    if review.reviewer_id != reviewer_id:
        raise PermissionError("You can only delete your own review.")

    reviewee_id = review.reviewee_id
    await db.delete(review)
    await db.flush()
    await _recompute_reputation(db, reviewee_id)
    await db.commit()

async def get_seller_reviews(db: AsyncSession, seller_id: UUID) -> List[dict]:
    """
    Returns real buyer reviews left for a seller (reviewee_id == seller_id), joined
    with the reviewer's name and the listing title, most recent first. Replaces the
    old hardcoded demo reviews shown on the seller dashboard's Reviews tab.
    """
    result = await db.execute(
        select(Review, User.full_name, Listing.title)
        .join(Order, Review.order_id == Order.id)
        .join(Listing, Order.listing_id == Listing.id)
        .join(User, User.id == Review.reviewer_id)
        .where(Review.reviewee_id == seller_id)
        .order_by(Review.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": str(review.id),
            "buyer_name": buyer_name,
            "rating": review.rating,
            "review_text": review.comment or "",
            "product_title": listing_title,
            "created_at": review.created_at,
            "seller_reply": review.seller_reply,
            "seller_replied_at": review.seller_replied_at,
        }
        for review, buyer_name, listing_title in rows
    ]

async def get_listing_reviews(db: AsyncSession, listing_id: UUID) -> List[dict]:
    """Returns real buyer reviews (with any seller reply) for a specific listing, for the product page."""
    result = await db.execute(
        select(Review, User.full_name)
        .join(Order, Review.order_id == Order.id)
        .join(User, User.id == Review.reviewer_id)
        .where(Order.listing_id == listing_id)
        .order_by(Review.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": str(review.id),
            "buyer_name": buyer_name,
            "rating": review.rating,
            "comment": review.comment,
            "seller_reply": review.seller_reply,
            "seller_replied_at": review.seller_replied_at,
            "created_at": review.created_at,
        }
        for review, buyer_name in rows
    ]

async def reply_to_review(db: AsyncSession, seller_id: UUID, review_id: UUID, reply_text: str) -> Review:
    """Saves the reviewed party's (usually the seller's) reply to a review, so it's visible to buyers on the product page."""
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalars().first()
    if not review:
        raise ValueError("Review not found.")
    if review.reviewee_id != seller_id:
        raise PermissionError("You can only reply to reviews left about you.")
    review.seller_reply = reply_text
    review.seller_replied_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(review)
    return review


# --- Negotiation Chat Services ---

async def get_or_create_chat(db: AsyncSession, buyer_id: UUID, seller_id: UUID, listing_id: Optional[UUID]) -> Chat:
    """Retrieves an existing chat session or creates a new one between a buyer and seller."""
    query = select(Chat).where(
        and_(
            Chat.buyer_id == buyer_id,
            Chat.seller_id == seller_id,
            Chat.listing_id == listing_id
        )
    )
    result = await db.execute(query)
    chat = result.scalars().first()
    
    if not chat:
        chat = Chat(buyer_id=buyer_id, seller_id=seller_id, listing_id=listing_id)
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        
    return chat

async def send_chat_message(db: AsyncSession, chat_id: UUID, sender_id: UUID, content: str) -> ChatMessage:
    """
    Sends a message in the chat room.
    Retrieves the recipient's preferred language and translates the message if they differ.
    """
    # Fetch chat room participants
    chat_res = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = chat_res.scalars().first()
    if not chat:
        raise ValueError("Chat room not found.")
        
    if sender_id not in [chat.buyer_id, chat.seller_id]:
        raise ValueError("Unauthorized message post.")

    # Determine recipient
    recipient_id = chat.seller_id if sender_id == chat.buyer_id else chat.buyer_id
    
    # Import user service dynamically
    from app.identity.service import get_user_by_id
    sender = await get_user_by_id(db, sender_id)
    recipient = await get_user_by_id(db, recipient_id)

    # Perform automated translation if languages differ
    translated_content = None
    if sender and recipient and sender.preferred_language != recipient.preferred_language:
        try:
            translated_content = await translate_message(
                content,
                source_lang=sender.preferred_language,
                target_lang=recipient.preferred_language
            )
        except Exception as e:
            logger.error(f"Translation failure: {e}")

    msg = ChatMessage(
        chat_id=chat.id,
        sender_id=sender_id,
        content=content,
        translated_content=translated_content
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg

async def get_chat_messages(db: AsyncSession, chat_id: UUID, current_user_id: UUID) -> List[ChatMessage]:
    """Retrieves all messages for a specific chat room, ensuring authorization."""
    chat_res = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = chat_res.scalars().first()
    if not chat:
        raise ValueError("Chat room not found.")
        
    if current_user_id not in [chat.buyer_id, chat.seller_id]:
        raise ValueError("Unauthorized access to chat room history.")
        
    msg_res = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.sent_at)
    )
    return list(msg_res.scalars().all())
