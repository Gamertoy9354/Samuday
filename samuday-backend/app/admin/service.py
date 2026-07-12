from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models import User
from app.marketplace.models import Listing, Order
from app.wallet.models import Wallet, LedgerEntry
from app.marketplace.fees import PLATFORM_HOUSE_USER_ID


async def list_sellers(db: AsyncSession, tier: Optional[str] = None, verification_status: Optional[str] = None) -> List[dict]:
    query = select(User).where(User.is_seller == True)  # noqa: E712
    if tier:
        query = query.where(User.seller_tier == tier)
    if verification_status:
        query = query.where(User.seller_verification_status == verification_status)
    query = query.order_by(User.created_at.desc())

    result = await db.execute(query)
    sellers = list(result.scalars().all())
    if not sellers:
        return []

    seller_ids = [s.id for s in sellers]
    count_result = await db.execute(
        select(Listing.seller_id, func.count(Listing.id))
        .where(Listing.seller_id.in_(seller_ids))
        .group_by(Listing.seller_id)
    )
    counts = dict(count_result.all())

    return [
        {
            "id": s.id,
            "full_name": s.full_name,
            "email": s.email,
            "phone_number": s.phone_number,
            "seller_tier": s.seller_tier,
            "seller_verification_status": s.seller_verification_status,
            "listing_count": counts.get(s.id, 0),
            "created_at": s.created_at,
        }
        for s in sellers
    ]


async def list_all_listings(db: AsyncSession, limit: int = 100) -> List[dict]:
    result = await db.execute(
        select(Listing).order_by(Listing.created_at.desc()).limit(limit)
    )
    listings = list(result.scalars().all())
    if not listings:
        return []

    seller_ids = list({l.seller_id for l in listings})
    users_result = await db.execute(select(User).where(User.id.in_(seller_ids)))
    names_by_id = {u.id: u.full_name for u in users_result.scalars().all()}

    return [
        {
            "id": l.id,
            "title": l.title,
            "seller_id": l.seller_id,
            "seller_name": names_by_id.get(l.seller_id),
            "price": l.price,
            "quantity": l.quantity,
            "status": l.status,
            "pillar": l.pillar,
            "created_at": l.created_at,
        }
        for l in listings
    ]


async def get_overview(db: AsyncSession) -> dict:
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_sellers = (await db.execute(select(func.count(User.id)).where(User.is_seller == True))).scalar() or 0  # noqa: E712
    official_sellers = (await db.execute(
        select(func.count(User.id)).where(User.seller_tier == "official")
    )).scalar() or 0
    local_sellers = (await db.execute(
        select(func.count(User.id)).where(User.seller_tier == "local")
    )).scalar() or 0
    pending_verifications = (await db.execute(
        select(func.count(User.id)).where(User.seller_verification_status == "pending")
    )).scalar() or 0

    total_listings = (await db.execute(select(func.count(Listing.id)))).scalar() or 0
    active_listings = (await db.execute(select(func.count(Listing.id)).where(Listing.status == "active"))).scalar() or 0

    total_orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    completed_orders = (await db.execute(select(func.count(Order.id)).where(Order.status == "completed"))).scalar() or 0
    gmv = (await db.execute(
        select(func.sum(Order.product_amount)).where(Order.status == "completed")
    )).scalar() or 0

    house_wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == PLATFORM_HOUSE_USER_ID))
    house_wallet = house_wallet_result.scalars().first()
    house_balance = house_wallet.balance if house_wallet else 0

    platform_fee_revenue = 0
    delivery_fee_collected = 0
    if house_wallet:
        fee_result = await db.execute(
            select(func.sum(LedgerEntry.amount)).where(
                and_(LedgerEntry.wallet_id == house_wallet.id, LedgerEntry.reference_type == "platform_fee")
            )
        )
        platform_fee_revenue = fee_result.scalar() or 0
        delivery_result = await db.execute(
            select(func.sum(LedgerEntry.amount)).where(
                and_(LedgerEntry.wallet_id == house_wallet.id, LedgerEntry.reference_type == "delivery_fee_collected")
            )
        )
        delivery_fee_collected = delivery_result.scalar() or 0

    return {
        "total_users": total_users,
        "total_sellers": total_sellers,
        "official_sellers": official_sellers,
        "local_sellers": local_sellers,
        "pending_verifications": pending_verifications,
        "total_listings": total_listings,
        "active_listings": active_listings,
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "gmv_paise": gmv,
        "platform_fee_revenue_paise": platform_fee_revenue,
        "delivery_fee_collected_paise": delivery_fee_collected,
        "platform_house_balance_paise": house_balance,
    }
