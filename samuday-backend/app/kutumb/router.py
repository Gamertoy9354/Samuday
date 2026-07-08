from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.identity.models import User
from app.kutumb.models import Family
from app.kutumb import service
from app.kutumb.schemas import (
    FamilyCreate, FamilyResponse, FamilyMemberCreate, FamilyMemberResponse,
    CommunityGroupCreate, CommunityGroupResponse,
    MatrimonialProfileCreate, MatrimonialProfileResponse,
    UserBlockCreate, UserBlockResponse,
    UserReportCreate, UserReportResponse
)

router = APIRouter(prefix="/kutumb", tags=["Kutumb Network"])

def map_family_response(family: Family) -> FamilyResponse:
    """Helper to convert Family model + members relationship to Pydantic Response schema."""
    return FamilyResponse(
        id=family.id,
        name=family.name,
        head_id=family.head_id,
        members=[FamilyMemberResponse.model_validate(m) for m in family.members] if family.members else [],
        created_at=family.created_at
    )


# --- Family Registry Endpoints ---

@router.post("/families", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
async def create_family_route(
    payload: FamilyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Registers a new family unit."""
    family = await service.create_family(db, current_user.id, payload)
    return map_family_response(family)

@router.post("/families/{family_id}/members", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_family_member_route(
    family_id: UUID,
    payload: FamilyMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Adds a family member relative. Gated to family head only."""
    try:
        member = await service.add_family_member(db, family_id, payload, current_user.id)
        return member
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/families/me", response_model=FamilyResponse)
async def get_my_family_route(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the family of the logged-in user."""
    family = await service.get_user_family(db, current_user.id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not associated with any family registry"
        )
    return map_family_response(family)


# --- Community Groups Endpoints ---

@router.post("/groups", response_model=CommunityGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group_route(
    payload: CommunityGroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Registers a community group (e.g. society, temple committee)."""
    group = await service.create_community_group(db, current_user.id, payload)
    return group

@router.get("/groups", response_model=List[CommunityGroupResponse])
async def get_groups_route(
    geohash_prefix: Optional[str] = Query(None, description="Prefix to filter groups by geohash proximity"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves groups, supporting geohash prefixes."""
    groups = await service.get_community_groups(db, geohash_prefix)
    return groups


# --- Matrimonial Registry Endpoints ---

@router.post("/matrimonial/opt-in", response_model=MatrimonialProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_matrimonial_profile_route(
    payload: MatrimonialProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Registers a matrimonial profile, verifying explicit opt-in confirmation."""
    try:
        profile = await service.create_matrimonial_profile(db, current_user.id, payload)
        return profile
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/matrimonial/search", response_model=List[MatrimonialProfileResponse])
async def search_matrimonial_route(
    gender: Optional[str] = Query(None, description="Filter by gender"),
    religion: Optional[str] = Query(None, description="Filter by religion"),
    caste: Optional[str] = Query(None, description="Filter by caste (optional)"),
    occupation: Optional[str] = Query(None, description="Filter by occupation"),
    verified_only: bool = Query(False, description="Filter for family_verified_badge profiles only"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Searches matrimonial profiles. Excludes mutually blocked profiles."""
    profiles = await service.search_matrimonial_profiles(
        db,
        current_user_id=current_user.id,
        gender=gender,
        religion=religion,
        caste=caste,
        occupation=occupation,
        verified_only=verified_only
    )
    return profiles


# --- Safety Blocking & Abuse Reporting Endpoints ---

@router.post("/blocks", response_model=UserBlockResponse, status_code=status.HTTP_201_CREATED)
async def block_user_route(
    payload: UserBlockCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Blocks another user account for safety."""
    try:
        block = await service.block_user(db, current_user.id, payload.blocked_user_id)
        return block
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/blocks", response_model=List[UserBlockResponse])
async def get_my_blocks_route(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists all blocked users."""
    blocks = await service.get_blocked_users(db, current_user.id)
    return blocks

@router.post("/reports", response_model=UserReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_report_route(
    payload: UserReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Files an abuse report against a peer user."""
    try:
        report = await service.submit_user_report(db, current_user.id, payload)
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
