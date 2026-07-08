from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.identity.models import User
from app.marketplace.models import Listing
from app.marketplace.schemas import ListingMediaResponse
from app.kisan import service
from app.kisan.schemas import (
    CropListingCreate, CropListingResponse,
    EquipmentListingCreate, EquipmentListingResponse,
    LoanApplicationCreate, LoanApplicationResponse,
    AdvisoryChatRequest, AdvisoryChatResponse
)

router = APIRouter(prefix="/kisan", tags=["Kisan Hub"])

def map_crop_listing_response(listing: Listing) -> CropListingResponse:
    """Helper to convert Listing + CropListing models into Pydantic schema."""
    return CropListingResponse(
        id=listing.id,
        seller_id=listing.seller_id,
        pillar=listing.pillar,
        category_id=listing.category_id,
        title=listing.title,
        description=listing.description,
        price=listing.price,
        listing_type=listing.listing_type,
        quantity=listing.quantity,
        unit=listing.unit,
        location_geohash=listing.location_geohash,
        status=listing.status,
        created_at=listing.created_at,
        media=[ListingMediaResponse.model_validate(m) for m in listing.media] if listing.media else [],
        crop_type=listing.crop_details.crop_type if listing.crop_details else "",
        grade=listing.crop_details.grade if listing.crop_details else "",
        harvest_date=listing.crop_details.harvest_date if listing.crop_details else datetime.now(timezone.utc),
        mandi_price_reference=listing.crop_details.mandi_price_reference if listing.crop_details else None
    )

def map_equipment_listing_response(listing: Listing) -> EquipmentListingResponse:
    """Helper to convert Listing + EquipmentListing models into Pydantic schema."""
    return EquipmentListingResponse(
        id=listing.id,
        seller_id=listing.seller_id,
        pillar=listing.pillar,
        category_id=listing.category_id,
        title=listing.title,
        description=listing.description,
        price=listing.price,
        listing_type=listing.listing_type,
        quantity=listing.quantity,
        unit=listing.unit,
        location_geohash=listing.location_geohash,
        status=listing.status,
        created_at=listing.created_at,
        media=[ListingMediaResponse.model_validate(m) for m in listing.media] if listing.media else [],
        equipment_type=listing.equipment_details.equipment_type if listing.equipment_details else "",
        rental_unit=listing.equipment_details.rental_unit if listing.equipment_details else "",
        operator_included=listing.equipment_details.operator_included if listing.equipment_details else False
    )


# --- Crop Listing Routes ---

@router.post("/listings/crop", response_model=CropListingResponse, status_code=status.HTTP_201_CREATED)
async def create_crop_listing_route(
    payload: CropListingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Creates a crop listing with grading details under the kisan pillar."""
    listing = await service.create_crop_listing(db, current_user.id, payload)
    return map_crop_listing_response(listing)

@router.get("/listings/crop", response_model=List[CropListingResponse])
async def get_crop_listings_route(db: AsyncSession = Depends(get_db)):
    """Retrieves all active crop listings."""
    listings = await service.get_crop_listings(db)
    return [map_crop_listing_response(l) for l in listings]


# --- Equipment Rental Routes ---

@router.post("/listings/equipment", response_model=EquipmentListingResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment_listing_route(
    payload: EquipmentListingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Creates an equipment rental listing under the kisan pillar."""
    listing = await service.create_equipment_listing(db, current_user.id, payload)
    return map_equipment_listing_response(listing)

@router.get("/listings/equipment", response_model=List[EquipmentListingResponse])
async def get_equipment_listings_route(db: AsyncSession = Depends(get_db)):
    """Retrieves all active machinery rental listings."""
    listings = await service.get_equipment_listings(db)
    return [map_equipment_listing_response(l) for l in listings]


# --- e-NAM Mandi Prices Feed ---

@router.get("/mandi-prices")
async def get_mandi_prices_route(
    crop_type: Optional[str] = Query(None, description="Filter by crop name, e.g. Wheat")
):
    """Retrieves current reference prices from the simulated e-NAM database."""
    return service.get_mandi_prices(crop_type)


# --- Farmer Micro-Loans Routes ---

@router.post("/loans/apply", response_model=LoanApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_for_loan_route(
    payload: LoanApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submits a farmer credit application, which is routed to partner lenders."""
    loan = await service.create_loan_application(db, current_user.id, payload)
    return loan

@router.get("/loans", response_model=List[LoanApplicationResponse])
async def get_loans_route(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all credit application files submitted by the farmer."""
    loans = await service.get_loan_applications(db, current_user.id)
    return loans


# --- Agricultural Advisor Chatbot ---

@router.post("/advisory/chat", response_model=AdvisoryChatResponse)
async def advisory_chat_route(
    payload: AdvisoryChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Agricultural advisor chatbot. Resolves responses in user's preferred language."""
    session = await service.get_crop_advisor_response(db, current_user.id, payload.query_text)
    return AdvisoryChatResponse(
        query_text=session.query_text,
        response_text=session.response_text,
        created_at=session.created_at
    )
