from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.middleware import t
from app.identity.models import User
from app.marketplace import service
from app.marketplace.models import Chat
from app.marketplace.upload_service import upload_service
from app.marketplace.schemas import (
    CategoryCreate, CategoryResponse, ListingCreate, ListingResponse,
    OrderCreate, OrderResponse, ReviewCreate, ReviewResponse,
    ChatCreate, ChatResponse, ChatMessageCreate, ChatMessageResponse
)

router = APIRouter(prefix="/marketplace", tags=["Marketplace Core"])

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Category Catalog Endpoints ---

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category_endpoint(payload: CategoryCreate, db: AsyncSession = Depends(get_db)):
    """Creates a new category category in the system catalog."""
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
        radius_km=radius_km
    )

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


# --- Orders & Escrow Endpoints ---

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

@router.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def submit_review_endpoint(
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submits buyer/seller peer review rating, dynamically adjusting user reputation metrics."""
    try:
        review = await service.submit_review(db, current_user.id, payload)
        return review
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


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
