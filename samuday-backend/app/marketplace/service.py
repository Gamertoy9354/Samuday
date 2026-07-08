import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.middleware import t
from app.identity.models import User, ReputationScore
from app.marketplace.models import Category, Listing, ListingMedia, Order, Review, Chat, ChatMessage
from app.marketplace.schemas import CategoryCreate, ListingCreate, OrderCreate, ReviewCreate
from app.wallet.service import hold_escrow, release_escrow, refund_escrow
from app.search.service import sync_listing_to_search
from app.ai.service import translate_message

logger = logging.getLogger(__name__)

# --- Category Tree Services ---

async def create_category(db: AsyncSession, cat_in: CategoryCreate) -> Category:
    """Creates a new category in the catalog tree."""
    category = Category(
        parent_id=cat_in.parent_id,
        name=cat_in.name,
        pillar=cat_in.pillar,
        icon_url=cat_in.icon_url
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category

async def get_categories(db: AsyncSession, pillar: Optional[str] = None) -> List[Category]:
    """Retrieves all categories, optionally filtered by pillar (kisan, sheshop, general)."""
    query = select(Category)
    if pillar:
        query = query.where(Category.pillar == pillar)
    result = await db.execute(query)
    return list(result.scalars().all())


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

    return db_listing

async def get_listings(
    db: AsyncSession,
    pillar: Optional[str] = None,
    category_id: Optional[UUID] = None,
    query: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: float = 5.0
) -> List[Listing]:
    """Retrieves active listings, filtering by pillar, category, search term, or geo radius."""
    if query or (lat is not None and lng is not None):
        # Retrieve matching listing IDs from Meilisearch
        from app.search.service import search_listings, client as meili_client
        q = query or ""
        hits = []
        try:
            if lat is not None and lng is not None:
                hits = await search_listings(q, lat, lng, radius_km)
            else:
                # Synchronous fallback for text search
                res = await asyncio.to_thread(
                    lambda: meili_client.index("listings").search(q)
                )
                hits = res.get("hits", [])
        except Exception as e:
            logger.error(f"Search retrieval failed: {e}")

        if hits:
            ids = [UUID(hit["id"]) for hit in hits]
            result = await db.execute(
                select(Listing)
                .options(selectinload(Listing.media), selectinload(Listing.category))
                .where(
                    and_(
                        Listing.id.in_(ids),
                        Listing.status == "active"
                    )
                )
            )
            db_listings = {l.id: l for l in result.scalars().all()}
            # Return maintaining Meilisearch sorted order
            return [db_listings[l_id] for l_id in ids if l_id in db_listings]
        return []

    db_query = (
        select(Listing)
        .options(selectinload(Listing.media), selectinload(Listing.category))
        .where(Listing.status == "active")
    )
    if pillar:
        db_query = db_query.where(Listing.pillar == pillar)
    if category_id:
        db_query = db_query.where(Listing.category_id == category_id)
        
    result = await db.execute(db_query)
    return list(result.scalars().all())

async def get_all_listings(db: AsyncSession, limit: int = 50) -> List[Listing]:
    """Retrieves all active listings with media and category preloaded."""
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media), selectinload(Listing.category))
        .where(Listing.status == "active")
        .limit(limit)
    )
    return list(result.scalars().all())

async def get_listing_by_id(db: AsyncSession, listing_id: UUID) -> Optional[Listing]:
    """Retrieves a listing by UUID."""
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media))
        .where(Listing.id == listing_id)
    )
    return result.scalars().first()


# --- Order & Escrow Services ---

async def create_order(db: AsyncSession, buyer_id: UUID, order_in: OrderCreate) -> Order:
    """
    Creates an order and places the buyer's funds in an escrow hold ledger account.
    Fails if buyer balance is insufficient.
    """
    listing = await get_listing_by_id(db, order_in.listing_id)
    if not listing:
        raise ValueError(t("listing.not_found"))
    if listing.status != "active":
        raise ValueError("Listing is no longer active.")
    if listing.seller_id == buyer_id:
        raise ValueError("You cannot purchase your own listing.")
    if listing.quantity < order_in.quantity:
        raise ValueError("Requested quantity exceeds available stock.")

    total_amount = listing.price * order_in.quantity
    
    order = Order(
        buyer_id=buyer_id,
        seller_id=listing.seller_id,
        listing_id=listing.id,
        quantity=order_in.quantity,
        total_amount=total_amount,
        status="pending",
        fulfillment_type=order_in.fulfillment_type
    )
    db.add(order)
    await db.flush()  # Generate order UUID

    # Deduct funds and record an escrow hold (rolls back transaction on failure)
    await hold_escrow(db, buyer_id, total_amount, order.id)

    order.status = "paid"  # Status changes from pending to paid since funds are escrow-secured
    await db.commit()
    await db.refresh(order)
    return order

async def complete_order(db: AsyncSession, order_id: UUID, current_user_id: UUID) -> Order:
    """Completes an order, releases escrow holds to the seller, and updates transaction counts."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise ValueError(t("order.not_found"))

    # Only buyer can confirm fulfillment/completion of order
    if order.buyer_id != current_user_id:
        raise ValueError("Only the buyer can mark the order completed.")

    if order.status != "paid":
        raise ValueError("Order must be in paid status to complete.")

    # Release escrow holds (credits seller)
    await release_escrow(db, order.id, order.seller_id)
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
    await db.commit()
    await db.refresh(order)
    return order


# --- Review & Peer Rating Services ---

async def submit_review(db: AsyncSession, reviewer_id: UUID, rev_in: ReviewCreate) -> Review:
    """Submits a rating and comment, and updates the reviewee's average reputation score."""
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

    # Recalculate average reputation score for the reviewee
    scores_query = select(func.avg(Review.rating), func.count(Review.id)).where(Review.reviewee_id == reviewee_id)
    score_res = await db.execute(scores_query)
    avg_rating, count = score_res.first()
    
    # Update or insert ReputationScore
    rep_result = await db.execute(
        select(ReputationScore).where(
            and_(ReputationScore.user_id == reviewee_id, ReputationScore.pillar == "aggregate")
        )
    )
    rep = rep_result.scalars().first()
    if rep:
        rep.score = float(avg_rating) if avg_rating is not None else 5.0
        # Incorporate ratings counts
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
