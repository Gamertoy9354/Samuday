from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.middleware import t
from app.core import geocoding
from app.identity.models import User
from app.marketplace import service
from app.marketplace.models import Chat
from app.marketplace.upload_service import upload_service
from app.marketplace.schemas import (
    CategoryCreate, CategoryResponse, ListingCreate, ListingResponse, ListingUpdate,
    OrderCreate, OrderResponse, OrderDetailResponse, ReviewCreate, ReviewUpdate, ReviewResponse, ReviewReplyCreate,
    ChatCreate, ChatResponse, ChatMessageCreate, ChatMessageResponse,
    AddressCreate, AddressResponse,
)

router = APIRouter(prefix="/marketplace", tags=["Marketplace Core"])

# --- Address Book ---

@router.get("/addresses", response_model=List[AddressResponse])
async def list_my_addresses(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Returns the current user's saved delivery addresses."""
    return await service.get_addresses(db, current_user.id)

@router.post("/addresses", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
async def create_address_endpoint(
    payload: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Saves a new delivery address for the current user."""
    return await service.create_address(db, current_user.id, payload)

@router.delete("/addresses/{address_id}")
async def delete_address_endpoint(
    address_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deletes one of the current user's saved addresses."""
    success = await service.delete_address(db, current_user.id, address_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found.")
    return {"status": "deleted"}

# --- Geocoding (GPS auto-detect / manual address search) ---

@router.get("/geocode/reverse")
async def reverse_geocode_endpoint(lat: float, lng: float):
    """Converts GPS coordinates (from the browser's Geolocation API) into a fillable address."""
    result = await geocoding.reverse_geocode(lat, lng)
    if not result:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not resolve an address for this location.")
    return result

@router.get("/geocode/search")
async def forward_geocode_endpoint(q: str = Query(..., min_length=3)):
    """Searches for addresses matching free-text input, for manual entry autocomplete."""
    return await geocoding.forward_geocode(q)

@router.post("/upload")
async def upload_listing_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Saves manually selected files directly to backend static storage.
    """
    try:
        url = await upload_service.save_file(file)
        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Category Catalog Endpoints ---

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category_endpoint(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new category in the system catalog. Requires authentication."""
    return await service.create_category(db, payload)

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories_endpoint(
    pillar: Optional[str] = Query(None, description="Filter by pillar"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all registered catalog categories."""
    import typing
    return await service.get_categories(db, pillar)


# --- Listings Endpoints ---

@router.post("/listings", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def create_listing_endpoint(
    payload: ListingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Creates a product or service listing, syncing it to the search database."""
    listing = await service.create_listing(db, current_user.id, payload)
    return listing

@router.get("/listings", response_model=List[ListingResponse])
async def get_listings_endpoint(
    pillar: Optional[str] = Query(None, description="Filter by pillar"),
    category_id: Optional[UUID] = Query(None, description="Filter by category ID"),
    query: Optional[str] = Query(None, description="Search keyword"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lng: Optional[float] = Query(None, description="Longitude"),
    radius_km: float = Query(5.0, description="Search radius in kilometers"),
    seller_tier: Optional[str] = Query(None, description="Filter by seller tier: official or local"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves active product and service listings with optional geo-radius search."""
    return await service.get_listings(
        db,
        pillar=pillar,
        category_id=category_id,
        query=query,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        seller_tier=seller_tier,
    )

@router.get("/sellers/{seller_id}")
async def get_seller_profile_endpoint(seller_id: UUID, db: AsyncSession = Depends(get_db)):
    """Public: returns a seller's storefront profile (name, avatar, tier, rating), for their public seller page."""
    profile = await service.get_seller_public_profile(db, seller_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found.")
    return profile

@router.get("/sellers/{seller_id}/listings", response_model=List[ListingResponse])
async def get_seller_listings_endpoint(seller_id: UUID, db: AsyncSession = Depends(get_db)):
    """Public: returns a seller's active listings, for their public storefront page."""
    return await service.get_seller_public_listings(db, seller_id)

@router.get("/listings/mine", response_model=List[ListingResponse])
async def get_my_listings_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns all of the current user's own listings regardless of status (active, paused, removed, sold), for the seller dashboard."""
    return await service.get_my_listings(db, current_user.id)

@router.get("/listings/{listing_id}", response_model=ListingResponse)
async def get_listing_endpoint(listing_id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieves details of a specific listing."""
    listing = await service.get_listing_by_id(db, listing_id)
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("listing.not_found")
        )
    return listing

@router.put("/listings/{listing_id}", response_model=ListingResponse)
async def update_listing_endpoint(
    listing_id: UUID,
    payload: ListingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Seller updates their own listing (price, description, offers, return policy, etc.)."""
    try:
        return await service.update_listing(db, current_user.id, listing_id, payload)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/listings/{listing_id}/pause", response_model=ListingResponse)
async def pause_listing_endpoint(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Temporarily takes a listing down from public view. Reversible — see /reactivate."""
    try:
        return await service.pause_listing(db, current_user.id, listing_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/listings/{listing_id}/reactivate", response_model=ListingResponse)
async def reactivate_listing_endpoint(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Brings a temporarily paused listing back to public view."""
    try:
        return await service.reactivate_listing(db, current_user.id, listing_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/listings/{listing_id}", response_model=ListingResponse)
async def remove_listing_endpoint(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Permanently takes a listing down. Not reversible — order history referencing it is preserved."""
    try:
        return await service.remove_listing_permanently(db, current_user.id, listing_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Orders & Escrow Endpoints ---

@router.get("/orders/mine", response_model=List[OrderDetailResponse])
async def get_my_orders_endpoint(
    role: str = Query("buyer", pattern="^(buyer|seller)$", description="View orders as buyer or seller"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns the current user's order history (as buyer or seller), with listing details."""
    return await service.get_orders_for_user(db, current_user.id, role)

@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order_endpoint(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Places an order, checking balance and transferring funds into transaction escrow."""
    try:
        order = await service.create_order(db, current_user.id, payload)
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/orders/{order_id}/complete", response_model=OrderResponse)
async def complete_order_endpoint(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark order completed by the buyer, triggering escrow disbursement to the seller."""
    try:
        order = await service.complete_order(db, order_id, current_user.id)
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order_endpoint(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancels a paid order and refunds the escrowed funds to the buyer."""
    try:
        order = await service.cancel_order(db, order_id, current_user.id)
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# --- Peer Reviews Endpoints ---

@router.get("/reviews/mine-as-seller")
async def get_my_seller_reviews_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns real buyer reviews left on the current user's listings (for the Seller Dashboard Reviews tab)."""
    return await service.get_seller_reviews(db, current_user.id)

@router.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def submit_review_endpoint(
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submits buyer/seller peer review rating, dynamically adjusting user reputation metrics. An AI reply is posted automatically — no seller action needed."""
    try:
        review = await service.submit_review(db, current_user.id, payload)
        return review
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review_endpoint(
    review_id: UUID,
    payload: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Buyer edits their own review. Recomputes the seller's reputation and has the AI draft a fresh reply automatically."""
    try:
        return await service.update_review(db, current_user.id, review_id, payload.rating, payload.comment)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review_endpoint(
    review_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Buyer deletes their own review, recomputing the seller's reputation afterward."""
    try:
        await service.delete_review(db, current_user.id, review_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/reviews/{review_id}/reply", response_model=ReviewResponse)
async def reply_to_review_endpoint(
    review_id: UUID,
    payload: ReviewReplyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Saves the seller's reply to a buyer review (AI-drafted or manual), visible to buyers on the product page."""
    try:
        return await service.reply_to_review(db, current_user.id, review_id, payload.reply)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/listings/{listing_id}/reviews")
async def get_listing_reviews_endpoint(listing_id: UUID, db: AsyncSession = Depends(get_db)):
    """Returns real buyer reviews (with any seller reply) for a specific listing, for the product page."""
    return await service.get_listing_reviews(db, listing_id)


# --- Negotiation Chat Endpoints ---

@router.post("/chats", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_endpoint(
    payload: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initializes or opens a chat channel between buyer and seller regarding a listing."""
    chat = await service.get_or_create_chat(
        db, buyer_id=current_user.id, seller_id=payload.seller_id, listing_id=payload.listing_id
    )
    return chat

@router.get("/chats", response_model=List[ChatResponse])
async def get_chats_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all chat rooms where the current user is a participant."""
    query = select(Chat).where(
        or_(Chat.buyer_id == current_user.id, Chat.seller_id == current_user.id)
    )
    result = await db.execute(query)
    return list(result.scalars().all())

@router.post("/chats/{chat_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_chat_message_endpoint(
    chat_id: UUID,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Posts a message to the chat channel, executing translations if preferred languages differ."""
    try:
        msg = await service.send_chat_message(db, chat_id, current_user.id, payload.content)
        return msg
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/chats/{chat_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages_endpoint(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all text message history for a specific negotiation channel."""
    try:
        messages = await service.get_chat_messages(db, chat_id, current_user.id)
        return messages
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
