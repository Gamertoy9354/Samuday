from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.identity.models import User
from app.admin import service
from app.admin.schemas import AdminSellerRow, AdminListingRow, AdminOverview

router = APIRouter(prefix="/admin", tags=["Platform Admin"])

@router.get("/overview", response_model=AdminOverview)
async def get_overview_endpoint(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Platform-wide stats: users, sellers, listings, orders, GMV, and fee revenue."""
    return await service.get_overview(db)

@router.get("/sellers", response_model=List[AdminSellerRow])
async def list_sellers_endpoint(
    tier: Optional[str] = Query(None, description="official or local"),
    verification_status: Optional[str] = Query(None, description="unverified, pending, approved, rejected"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists all sellers, optionally filtered by tier/verification status."""
    return await service.list_sellers(db, tier, verification_status)

@router.get("/listings", response_model=List[AdminListingRow])
async def list_listings_endpoint(
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists all marketplace listings across all sellers, most recent first."""
    return await service.list_all_listings(db, limit)
