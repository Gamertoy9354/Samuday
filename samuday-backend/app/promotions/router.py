from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.identity.models import User
from app.promotions import service
from app.promotions.schemas import (
    SaleEventCreate, SaleEventResponse,
    AdvertisementCreate, AdvertisementResponse,
    SaleEventDetailResponse, AdDetailResponse
)

router = APIRouter(prefix="/promotions", tags=["Promotions & Ads"])

# --- Sale Events ---

@router.post("/sales", response_model=SaleEventResponse, status_code=status.HTTP_201_CREATED)
async def create_sale_event_endpoint(
    payload: SaleEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Seller creates a sale event with discount and date range."""
    event = await service.create_sale_event(db, current_user.id, payload)
    return event

@router.get("/sales", response_model=List[SaleEventResponse])
async def get_active_sales_endpoint(db: AsyncSession = Depends(get_db)):
    """Public: returns currently active sale events for homepage."""
    events = await service.get_active_sale_events(db)
    return events

@router.get("/sales/mine", response_model=List[SaleEventResponse])
async def get_my_sales_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Seller: returns their own sale events."""
    events = await service.get_seller_sale_events(db, current_user.id)
    return events

@router.get("/sales/{sale_id}", response_model=SaleEventDetailResponse)
async def get_sale_event_detail_endpoint(sale_id: UUID, db: AsyncSession = Depends(get_db)):
    """Public: returns a sale event plus all the listings it applies to, for its dynamic detail page."""
    detail = await service.get_sale_event_detail(db, sale_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale event not found.")
    return detail

@router.delete("/sales/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sale_event_endpoint(
    sale_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Seller takes down (deletes) one of their own sale events."""
    try:
        await service.delete_sale_event(db, current_user.id, sale_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# --- Advertisements ---

@router.post("/ads", response_model=AdvertisementResponse, status_code=status.HTTP_201_CREATED)
async def create_advertisement_endpoint(
    payload: AdvertisementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Seller purchases an ad placement on the homepage."""
    ad = await service.create_advertisement(db, current_user.id, payload)
    return ad

@router.get("/ads", response_model=List[AdvertisementResponse])
async def get_active_ads_endpoint(
    placement: Optional[str] = Query(None, description="hero_banner, sidebar, category_strip"),
    db: AsyncSession = Depends(get_db)
):
    """Public: returns active advertisements, optionally filtered by placement."""
    ads = await service.get_active_advertisements(db, placement)
    return ads

@router.post("/ads/{ad_id}/click")
async def record_ad_click_endpoint(ad_id: UUID, db: AsyncSession = Depends(get_db)):
    """Records a click on an advertisement for analytics."""
    success = await service.record_ad_click(db, ad_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advertisement not found")
    return {"status": "click_recorded"}

@router.get("/ads/mine", response_model=List[AdvertisementResponse])
async def get_my_ads_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Seller: returns their own advertisements."""
    ads = await service.get_seller_advertisements(db, current_user.id)
    return ads

@router.get("/ads/{ad_id}", response_model=AdDetailResponse)
async def get_ad_detail_endpoint(ad_id: UUID, db: AsyncSession = Depends(get_db)):
    """Public: returns an advertisement plus its linked listing (if any), for its dynamic detail page."""
    detail = await service.get_ad_detail(db, ad_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advertisement not found.")
    return detail

@router.delete("/ads/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_advertisement_endpoint(
    ad_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Seller takes down (deletes) one of their own advertisements."""
    try:
        await service.delete_advertisement(db, current_user.id, ad_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
