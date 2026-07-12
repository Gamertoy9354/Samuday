from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.identity.models import User
from app.kutumb.models import Family
from app.kutumb import service
from app.kutumb.schemas import (
    FamilyCreate, FamilyResponse, FamilyMemberCreate, FamilyMemberResponse,
    FamilyMemberVisibilityUpdate, FamilyInviteRespond,
    CommunityGroupCreate, CommunityGroupResponse,
    MatrimonialOptIn, MatrimonialProfileUpdate, MatrimonialProfileResponse,
    MatrimonialInterestCreate, MatrimonialInterestRespond, MatrimonialInterestResponse, MatrimonialInterestWithProfile,
    UserBlockCreate, UserBlockResponse,
    UserReportCreate, UserReportResponse,
    AdminReportRow, AdminReportResolve,
)

router = APIRouter(prefix="/kutumb", tags=["Kutumb Network"])


def _http_error(e: Exception) -> HTTPException:
    if isinstance(e, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    if isinstance(e, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def map_family_response(family: Family) -> FamilyResponse:
    return FamilyResponse(
        id=family.id,
        name=family.name,
        head_id=family.head_id,
        members=[FamilyMemberResponse.model_validate(m) for m in family.members] if family.members else [],
        created_at=family.created_at,
    )


# ===========================================================================
# Family Registry
# ===========================================================================

@router.post("/families", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
async def create_family_route(
    payload: FamilyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registers a new family unit."""
    family = await service.create_family(db, current_user.id, payload)
    return map_family_response(family)


@router.post("/families/{family_id}/members", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_family_member_route(
    family_id: UUID,
    payload: FamilyMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Adds a family member. Gated to the family head. Linking an existing account requires that account's acceptance."""
    try:
        return await service.add_family_member(db, family_id, payload, current_user.id)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


@router.get("/families/me", response_model=FamilyResponse)
async def get_my_family_route(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves the family of the logged-in user (as head or accepted member)."""
    family = await service.get_user_family(db, current_user.id)
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You are not associated with any family registry")
    return map_family_response(family)


@router.get("/families/invites", response_model=List[FamilyMemberResponse])
async def get_family_invites_route(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists pending family-link invites addressed to the current account, awaiting accept/decline."""
    return await service.get_pending_family_invites(db, current_user.id)


@router.post("/families/members/{member_id}/respond", response_model=FamilyMemberResponse)
async def respond_family_invite_route(
    member_id: UUID,
    payload: FamilyInviteRespond,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accepts or declines being linked to a family. Only the addressed account holder may respond."""
    try:
        return await service.respond_to_family_invite(db, member_id, current_user.id, payload.accept)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


@router.patch("/families/members/{member_id}/visibility", response_model=FamilyMemberResponse)
async def update_family_member_visibility_route(
    member_id: UUID,
    payload: FamilyMemberVisibilityUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates phone/KYC visibility for a family member — only the member themself, or the head for account-less members."""
    try:
        return await service.update_family_member_visibility(db, member_id, current_user.id, payload)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


# ===========================================================================
# Community Groups
# ===========================================================================

@router.post("/groups", response_model=CommunityGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group_route(
    payload: CommunityGroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registers a community group (e.g. society, temple committee). Creator is auto-joined as admin."""
    return await service.create_community_group(db, current_user.id, payload)


@router.get("/groups", response_model=List[CommunityGroupResponse])
async def get_groups_route(
    geohash_prefix: Optional[str] = Query(None, description="Prefix to filter groups by geohash proximity"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves groups, supporting geohash prefixes, with membership counts and current-user membership state."""
    return await service.get_community_groups(db, geohash_prefix, current_user.id)


@router.get("/groups/mine", response_model=List[CommunityGroupResponse])
async def get_my_groups_route(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists groups the current user has joined."""
    return await service.get_my_groups(db, current_user.id)


@router.post("/groups/{group_id}/join", response_model=CommunityGroupResponse)
async def join_group_route(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.join_community_group(db, group_id, current_user.id)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


@router.post("/groups/{group_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_group_route(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await service.leave_community_group(db, group_id, current_user.id)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


# ===========================================================================
# Matrimonial Registry
# ===========================================================================

async def require_matrimonial_access(current_user: User = Depends(get_current_user)) -> User:
    """
    Shared gate for every matrimonial route. Re-derived from the live user record on every
    request (never a cached login-time flag) — actual age/KYC eligibility is re-verified
    inside the service layer at the specific points that create or reactivate a profile.
    """
    return current_user


@router.post("/matrimonial/opt-in", response_model=MatrimonialProfileResponse, status_code=status.HTTP_201_CREATED)
async def opt_in_matrimonial_route(
    payload: MatrimonialOptIn,
    current_user: User = Depends(require_matrimonial_access),
    db: AsyncSession = Depends(get_db),
):
    """Registers a matrimonial profile. Age/KYC eligibility and consent are re-verified server-side on every call."""
    try:
        return await service.create_matrimonial_profile(db, current_user, payload)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


@router.get("/matrimonial/me", response_model=MatrimonialProfileResponse)
async def get_my_matrimonial_profile_route(
    current_user: User = Depends(require_matrimonial_access),
    db: AsyncSession = Depends(get_db),
):
    profile = await service.get_my_matrimonial_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matrimonial profile found")
    return profile


@router.patch("/matrimonial/me", response_model=MatrimonialProfileResponse)
async def update_matrimonial_profile_route(
    payload: MatrimonialProfileUpdate,
    current_user: User = Depends(require_matrimonial_access),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.update_matrimonial_profile(db, current_user.id, payload)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


@router.post("/matrimonial/opt-out", status_code=status.HTTP_204_NO_CONTENT)
async def opt_out_matrimonial_route(
    current_user: User = Depends(require_matrimonial_access),
    db: AsyncSession = Depends(get_db),
):
    """Immediately deactivates the profile — removed from discovery and pending interests within this same request."""
    try:
        await service.opt_out_matrimonial(db, current_user.id)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


@router.get("/matrimonial/search", response_model=List[MatrimonialProfileResponse])
async def search_matrimonial_route(
    gender: Optional[str] = Query(None),
    religion: Optional[str] = Query(None),
    caste: Optional[str] = Query(None),
    occupation: Optional[str] = Query(None),
    verified_only: bool = Query(False),
    min_age: Optional[int] = Query(None, ge=18, le=120),
    max_age: Optional[int] = Query(None, ge=18, le=120),
    current_user: User = Depends(require_matrimonial_access),
    db: AsyncSession = Depends(get_db),
):
    """Searches matrimonial profiles. Excludes mutually blocked profiles at the query level."""
    return await service.search_matrimonial_profiles(
        db, viewer=current_user, gender=gender, religion=religion, caste=caste,
        occupation=occupation, verified_only=verified_only, min_age=min_age, max_age=max_age,
    )


@router.post("/matrimonial/interests", response_model=MatrimonialInterestResponse, status_code=status.HTTP_201_CREATED)
async def send_interest_route(
    payload: MatrimonialInterestCreate,
    current_user: User = Depends(require_matrimonial_access),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.send_interest(db, current_user, payload.to_user_id)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


@router.get("/matrimonial/interests", response_model=List[MatrimonialInterestWithProfile])
async def get_my_interests_route(
    direction: str = Query("received", pattern="^(sent|received)$"),
    current_user: User = Depends(require_matrimonial_access),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_my_interests(db, current_user.id, direction)


@router.patch("/matrimonial/interests/{interest_id}", response_model=MatrimonialInterestResponse)
async def respond_interest_route(
    interest_id: UUID,
    payload: MatrimonialInterestRespond,
    current_user: User = Depends(require_matrimonial_access),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.respond_to_interest(db, current_user.id, interest_id, payload.action)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


# ===========================================================================
# Safety: Blocking & Abuse Reporting
# ===========================================================================

@router.post("/blocks", response_model=UserBlockResponse, status_code=status.HTTP_201_CREATED)
async def block_user_route(
    payload: UserBlockCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Blocks another user account for safety. Immediate and mutual for discovery purposes."""
    try:
        return await service.block_user(db, current_user.id, payload.blocked_user_id)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


@router.get("/blocks", response_model=List[UserBlockResponse])
async def get_my_blocks_route(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_blocked_users(db, current_user.id)


@router.delete("/blocks/{blocked_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_user_route(
    blocked_user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.unblock_user(db, current_user.id, blocked_user_id)


@router.post("/reports", response_model=UserReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_report_route(
    payload: UserReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Files an abuse report. 'underage_suspicion' immediately suspends any matrimonial profile pending review."""
    try:
        return await service.submit_user_report(db, current_user.id, payload)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)


# ===========================================================================
# Admin Moderation
# ===========================================================================

@router.get("/admin/reports", response_model=List[AdminReportRow])
async def list_admin_reports_route(
    report_status: Optional[str] = Query(None, alias="status"),
    reason_code: Optional[str] = Query(None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_reports(db, report_status, reason_code)


@router.post("/admin/reports/{report_id}/resolve", response_model=UserReportResponse)
async def resolve_admin_report_route(
    report_id: UUID,
    payload: AdminReportResolve,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.resolve_report(db, current_user.id, report_id, payload.action, payload.note)
    except (LookupError, PermissionError, ValueError) as e:
        raise _http_error(e)
