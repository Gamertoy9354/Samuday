import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.identity.models import KYCRecord
from app.kutumb.models import Family, FamilyMember, CommunityGroup, MatrimonialProfile, UserBlock, UserReport
from app.kutumb.schemas import FamilyCreate, FamilyMemberCreate, CommunityGroupCreate, MatrimonialProfileCreate, UserReportCreate

logger = logging.getLogger(__name__)

# --- Family Registry Service ---

async def create_family(db: AsyncSession, head_id: UUID, family_in: FamilyCreate) -> Family:
    """Registers a new family unit owned by the family head."""
    family = Family(
        name=family_in.name,
        head_id=head_id
    )
    db.add(family)
    await db.commit()
    
    # Eagerly load relationship to avoid lazy-loading on serialization
    result = await db.execute(
        select(Family)
        .options(selectinload(Family.members))
        .where(Family.id == family.id)
    )
    return result.scalars().first()

async def add_family_member(
    db: AsyncSession,
    family_id: UUID,
    member_in: FamilyMemberCreate,
    current_user_id: UUID
) -> FamilyMember:
    """Links a member to the family. Gated: Only the family head is allowed to add members."""
    # Find family
    fam_result = await db.execute(select(Family).where(Family.id == family_id))
    family = fam_result.scalars().first()
    if not family:
        raise ValueError("Family registry not found")
        
    if family.head_id != current_user_id:
        raise ValueError("Permission denied: Only the family head can link members")

    member = FamilyMember(
        family_id=family_id,
        user_id=member_in.user_id,
        relationship_type=member_in.relationship_type,
        display_name=member_in.display_name,
        visible_phone=member_in.visible_phone,
        visible_kyc=member_in.visible_kyc
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member

async def get_family(db: AsyncSession, family_id: UUID) -> Optional[Family]:
    """Retrieves a family preloading its member links."""
    result = await db.execute(
        select(Family)
        .options(selectinload(Family.members))
        .where(Family.id == family_id)
    )
    return result.scalars().first()

async def get_user_family(db: AsyncSession, user_id: UUID) -> Optional[Family]:
    """Retrieves the family a user belongs to (as either the head or a linked member)."""
    # 1. Check if member link exists
    mem_result = await db.execute(select(FamilyMember).where(FamilyMember.user_id == user_id))
    member_link = mem_result.scalars().first()
    
    if member_link:
        fam_id = member_link.family_id
    else:
        # 2. Check if user is the head
        fam_head_result = await db.execute(select(Family).where(Family.head_id == user_id))
        family = fam_head_result.scalars().first()
        if not family:
            return None
        fam_id = family.id

    return await get_family(db, fam_id)


# --- Community Groups Service ---

async def create_community_group(db: AsyncSession, creator_id: UUID, group_in: CommunityGroupCreate) -> CommunityGroup:
    """Creates a neighborhood society or temple association group."""
    group = CommunityGroup(
        name=group_in.name,
        group_type=group_in.group_type,
        description=group_in.description,
        location_geohash=group_in.location_geohash,
        created_by=creator_id
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group

async def get_community_groups(db: AsyncSession, geohash_prefix: Optional[str] = None) -> List[CommunityGroup]:
    """Retrieves community groups, optionally filtering by geohash prefix for proximity search."""
    db_query = select(CommunityGroup)
    if geohash_prefix:
        db_query = db_query.where(CommunityGroup.location_geohash.like(f"{geohash_prefix}%"))
    result = await db.execute(db_query)
    return list(result.scalars().all())


# --- Matrimonial Profile Service ---

async def create_matrimonial_profile(
    db: AsyncSession,
    user_id: UUID,
    profile_in: MatrimonialProfileCreate
) -> MatrimonialProfile:
    """Registers a matrimonial profile. Validates explicit user consent and calculates the family verified badge."""
    if not profile_in.opt_in_confirmed:
        raise ValueError("Consent required: You must check the matrimonial opt-in box to proceed")

    # Check if profile already exists
    existing_result = await db.execute(select(MatrimonialProfile).where(MatrimonialProfile.user_id == user_id))
    if existing_result.scalars().first():
        raise ValueError("A matrimonial profile already exists for this account")

    # Calculate family verified badge: True if linked family head is KYC approved
    family_verified = False
    family = await get_user_family(db, user_id)
    if family:
        # Check head's KYC status
        kyc_result = await db.execute(
            select(KYCRecord).where(
                and_(
                    KYCRecord.user_id == family.head_id,
                    KYCRecord.verification_status == "approved"
                )
            )
        )
        if kyc_result.scalars().first():
            family_verified = True

    profile = MatrimonialProfile(
        user_id=user_id,
        gender=profile_in.gender,
        birth_date=profile_in.birth_date,
        religion=profile_in.religion,
        caste=profile_in.caste,
        occupation=profile_in.occupation,
        education=profile_in.education,
        family_verified_badge=family_verified,
        opt_in_confirmed=True
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

async def search_matrimonial_profiles(
    db: AsyncSession,
    current_user_id: UUID,
    gender: Optional[str] = None,
    religion: Optional[str] = None,
    caste: Optional[str] = None,
    occupation: Optional[str] = None,
    verified_only: bool = False
) -> List[MatrimonialProfile]:
    """
    Searches for matrimonial candidates.
    Applies mutual block filtering: excludes blocked profiles and profiles that have blocked the searcher.
    """
    # 1. Fetch user blocks
    blocked_result = await db.execute(select(UserBlock.blocked_user_id).where(UserBlock.user_id == current_user_id))
    blockers_result = await db.execute(select(UserBlock.user_id).where(UserBlock.blocked_user_id == current_user_id))
    
    excluded_user_ids = set(blocked_result.scalars().all()) | set(blockers_result.scalars().all())
    excluded_user_ids.add(current_user_id)  # Exclude self

    # 2. Build search query
    db_query = select(MatrimonialProfile).where(
        and_(
            MatrimonialProfile.user_id.notin_(list(excluded_user_ids)),
            MatrimonialProfile.opt_in_confirmed == True
        )
    )

    if gender:
        db_query = db_query.where(MatrimonialProfile.gender == gender)
    if religion:
        db_query = db_query.where(MatrimonialProfile.religion == religion)
    if caste:
        db_query = db_query.where(MatrimonialProfile.caste == caste)
    if occupation:
        db_query = db_query.where(MatrimonialProfile.occupation == occupation)
    if verified_only:
        db_query = db_query.where(MatrimonialProfile.family_verified_badge == True)

    result = await db.execute(db_query)
    return list(result.scalars().all())


# --- Safety Blocking & Abuse Reporting ---

async def block_user(db: AsyncSession, user_id: UUID, blocked_user_id: UUID) -> UserBlock:
    """Places a safety block on a peer user."""
    if user_id == blocked_user_id:
        raise ValueError("You cannot block yourself")

    # Check if block exists
    exists_result = await db.execute(
        select(UserBlock).where(
            and_(
                UserBlock.user_id == user_id,
                UserBlock.blocked_user_id == blocked_user_id
            )
        )
    )
    existing = exists_result.scalars().first()
    if existing:
        return existing

    block = UserBlock(user_id=user_id, blocked_user_id=blocked_user_id)
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return block

async def get_blocked_users(db: AsyncSession, user_id: UUID) -> List[UserBlock]:
    """Retrieves all blocks filed by the user."""
    result = await db.execute(select(UserBlock).where(UserBlock.user_id == user_id))
    return list(result.scalars().all())

async def submit_user_report(db: AsyncSession, reporter_id: UUID, report_in: UserReportCreate) -> UserReport:
    """Logs an abuse report against a peer user."""
    if reporter_id == report_in.reported_user_id:
        raise ValueError("You cannot report yourself")

    report = UserReport(
        reporter_id=reporter_id,
        reported_user_id=report_in.reported_user_id,
        reason=report_in.reason,
        status="pending"
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report
