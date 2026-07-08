import logging
from typing import List
from uuid import UUID
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cart.models import CartItem
from app.cart.schemas import CartItemResponse, CartSummaryResponse
from app.marketplace.models import Listing, ListingMedia

logger = logging.getLogger(__name__)

async def add_to_cart(db: AsyncSession, user_id: UUID, listing_id: UUID, quantity: int = 1) -> CartItem:
    """Add an item to cart, or update quantity if already exists."""
    result = await db.execute(
        select(CartItem).where(
            and_(CartItem.user_id == user_id, CartItem.listing_id == listing_id)
        )
    )
    existing = result.scalars().first()
    
    if existing:
        existing.quantity += quantity
        await db.commit()
        await db.refresh(existing)
        return existing
    
    item = CartItem(user_id=user_id, listing_id=listing_id, quantity=quantity)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

async def get_cart(db: AsyncSession, user_id: UUID) -> CartSummaryResponse:
    """Get cart with joined listing details."""
    result = await db.execute(
        select(CartItem).where(CartItem.user_id == user_id)
        .options(selectinload(CartItem.listing).selectinload(Listing.media))
        .order_by(CartItem.added_at.desc())
    )
    cart_items = result.scalars().all()
    
    items = []
    total = 0
    count = 0
    
    for ci in cart_items:
        listing = ci.listing
        image = None
        if listing and listing.media:
            image = listing.media[0].media_url if listing.media else None
        
        item_resp = CartItemResponse(
            id=ci.id,
            user_id=ci.user_id,
            listing_id=ci.listing_id,
            quantity=ci.quantity,
            added_at=ci.added_at,
            listing_title=listing.title if listing else None,
            listing_price=listing.price if listing else 0,
            listing_image=image,
            seller_id=listing.seller_id if listing else None
        )
        items.append(item_resp)
        if listing:
            total += listing.price * ci.quantity
            count += ci.quantity
    
    return CartSummaryResponse(items=items, total_items=count, subtotal_paise=total)

async def update_cart_item(db: AsyncSession, user_id: UUID, item_id: UUID, quantity: int) -> CartItem:
    """Update quantity of a cart item."""
    result = await db.execute(
        select(CartItem).where(and_(CartItem.id == item_id, CartItem.user_id == user_id))
    )
    item = result.scalars().first()
    if not item:
        raise ValueError("Cart item not found")
    
    item.quantity = quantity
    await db.commit()
    await db.refresh(item)
    return item

async def remove_from_cart(db: AsyncSession, user_id: UUID, item_id: UUID) -> bool:
    """Remove an item from cart."""
    result = await db.execute(
        select(CartItem).where(and_(CartItem.id == item_id, CartItem.user_id == user_id))
    )
    item = result.scalars().first()
    if not item:
        return False
    
    await db.delete(item)
    await db.commit()
    return True

async def clear_cart(db: AsyncSession, user_id: UUID) -> int:
    """Remove all items from a user's cart."""
    result = await db.execute(
        delete(CartItem).where(CartItem.user_id == user_id)
    )
    await db.commit()
    return result.rowcount

async def get_cart_count(db: AsyncSession, user_id: UUID) -> int:
    """Get total number of items in cart."""
    result = await db.execute(
        select(CartItem).where(CartItem.user_id == user_id)
    )
    items = result.scalars().all()
    return sum(i.quantity for i in items)
