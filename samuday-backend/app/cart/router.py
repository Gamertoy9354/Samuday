from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.identity.models import User
from app.cart import service
from app.cart.schemas import CartItemAdd, CartItemUpdate, CartSummaryResponse

router = APIRouter(prefix="/cart", tags=["Shopping Cart"])

@router.get("", response_model=CartSummaryResponse)
async def get_cart_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns the current user's shopping cart with item details."""
    return await service.get_cart(db, current_user.id)

@router.post("", status_code=status.HTTP_201_CREATED)
async def add_to_cart_endpoint(
    payload: CartItemAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Adds an item to the cart (or increments quantity if already in cart)."""
    try:
        item = await service.add_to_cart(db, current_user.id, payload.listing_id, payload.quantity)
        return {"status": "added", "item_id": str(item.id), "quantity": item.quantity}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{item_id}")
async def update_cart_item_endpoint(
    item_id: UUID,
    payload: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates the quantity of a cart item."""
    try:
        item = await service.update_cart_item(db, current_user.id, item_id, payload.quantity)
        return {"status": "updated", "quantity": item.quantity}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete("/{item_id}")
async def remove_from_cart_endpoint(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Removes an item from the cart."""
    success = await service.remove_from_cart(db, current_user.id, item_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    return {"status": "removed"}

@router.delete("")
async def clear_cart_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clears all items from the cart."""
    count = await service.clear_cart(db, current_user.id)
    return {"status": "cleared", "removed_count": count}

@router.get("/count")
async def get_cart_count_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns the total number of items in the cart."""
    count = await service.get_cart_count(db, current_user.id)
    return {"count": count}
