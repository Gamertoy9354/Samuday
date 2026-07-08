from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.identity.models import User
from app.enterprise import service
from app.enterprise.schemas import (
    SupplierProfileCreate, SupplierProfileResponse,
    SupplierDashboardMetrics, AuditLogResponse
)
from app.ai.service import parse_voice_to_listing

router = APIRouter(prefix="/enterprise", tags=["Enterprise & Audits"])

@router.post("/supplier/profile", response_model=SupplierProfileResponse, status_code=status.HTTP_201_CREATED)
async def register_supplier_profile(
    payload: SupplierProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Registers a commercial supplier/business profile."""
    profile = await service.create_supplier_profile(db, current_user.id, payload)
    return profile

@router.get("/supplier/dashboard", response_model=SupplierDashboardMetrics)
async def get_supplier_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves business statistics and analytics for the logged-in supplier."""
    dashboard = await service.get_supplier_dashboard(db, current_user.id)
    return dashboard

@router.get("/admin/audits", response_model=List[AuditLogResponse])
async def list_administrative_audits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists security and transaction audits for system monitoring."""
    # Note: Under a real production application, this endpoint would verify administrative roles.
    # In the MVP environment, any authenticated user is allowed.
    audits = await service.get_audit_logs(db)
    return audits

@router.post("/voice-parse")
async def parse_voice_listing_endpoint(
    audio_url: str,
    current_user: User = Depends(get_current_user)
):
    """Parses/transcribes audio recording URL into listing parameters."""
    return await parse_voice_to_listing(audio_url)

