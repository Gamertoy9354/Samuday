from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.identity.models import User
from app.enterprise import service
from app.enterprise.schemas import (
    SupplierProfileCreate, SupplierProfileResponse, SupplierVerificationReviewRequest,
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

@router.get("/admin/verifications/pending", response_model=List[SupplierProfileResponse])
async def list_pending_supplier_verifications_endpoint(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin: lists pending Official-tier business verifications for review."""
    return await service.list_pending_supplier_verifications(db)

@router.post("/admin/verifications/{profile_id}/approve", response_model=SupplierProfileResponse)
async def approve_supplier_verification_endpoint(
    profile_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin: approves an Official-tier business verification."""
    try:
        return await service.review_supplier_verification(db, profile_id, current_user.id, approve=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/admin/verifications/{profile_id}/reject", response_model=SupplierProfileResponse)
async def reject_supplier_verification_endpoint(
    profile_id: UUID,
    payload: SupplierVerificationReviewRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin: rejects an Official-tier business verification with a reason."""
    try:
        return await service.review_supplier_verification(db, profile_id, current_user.id, approve=False, rejection_reason=payload.rejection_reason)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/admin/audits", response_model=List[AuditLogResponse])
async def list_administrative_audits(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists security and transaction audits for system monitoring. Admins only."""
    audits = await service.get_audit_logs(db)
    return audits

@router.post("/voice-parse")
async def parse_voice_listing_endpoint(
    audio_url: str,
    current_user: User = Depends(get_current_user)
):
    """Parses/transcribes audio recording URL into listing parameters."""
    return await parse_voice_to_listing(audio_url)

