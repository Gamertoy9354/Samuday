import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.identity.models import User, KYCRecord
from app.kutumb.models import (
    Family, FamilyMember, CommunityGroup, CommunityGroupMember,
    MatrimonialProfile, MatrimonialInterest, UserBlock, UserReport
)
from app.kutumb.schemas import (
    FamilyCreate, FamilyMemberCreate, FamilyMemberVisibilityUpdate,
    CommunityGroupCreate, MatrimonialOptIn, MatrimonialProfileUpdate, UserReportCreate
)

logger = logging.getLogger(__name__)

DAILY_INTEREST_LIMIT = 20


# ===========================================================================
# Family Registry
# ===========================================================================

async def create_family(db: AsyncSession, head_id: UUID, family_in: FamilyCreate) -> Family:
    """Registers a new family unit owned by the family head."""
    family = Family(name=family_in.name, head_id=head_id)
    db.add(family)
    await db.commit()

    result = await db.execute(
        select(Family).options(selectinload(Family.members)).where(Family.id == family.id)
    )
    return result.scalars().first()


async def add_family_member(
    db: AsyncSession, family_id: UUID, member_in: FamilyMemberCreate, current_user_id: UUID
) -> FamilyMember:
    """
    Links a member to the family. Only the family head may add members.
    If the member has their own app account, the link starts 'pending' and requires
    that account holder's explicit acceptance before it's treated as confirmed —
    the head cannot set visibility for that account on their behalf.
    """
    fam_result = await db.execute(select(Family).where(Family.id == family_id))
    family = fam_result.scalars().first()
    if not family:
        raise LookupError("Family registry not found")
    if family.head_id != current_user_id:
        raise PermissionError("Only the family head can link members")

    has_account = member_in.user_id is not None
    member = FamilyMember(
        family_id=family_id,
        user_id=member_in.user_id,
        relationship_type=member_in.relationship_type,
        display_name=member_in.display_name,
        # A head can only set visibility directly for account-less placeholder members.
        # For a linked account holder, visibility starts private and must be set by that person.
        visible_phone=(member_in.visible_phone if not has_account else False),
        visible_kyc=(member_in.visible_kyc if not has_account else False),
        status="pending" if has_account else "accepted",
        added_by_user_id=current_user_id,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def respond_to_family_invite(db: AsyncSession, member_id: UUID, current_user_id: UUID, accept: bool) -> FamilyMember:
    """Lets a linked account holder accept or decline being attached to a family."""
    result = await db.execute(select(FamilyMember).where(FamilyMember.id == member_id))
    member = result.scalars().first()
    if not member:
        raise LookupError("Family invite not found")
    if member.user_id != current_user_id:
        raise PermissionError("This invite isn't addressed to you")
    if member.status != "pending":
        raise ValueError("This invite has already been responded to")

    member.status = "accepted" if accept else "declined"
    member.responded_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(member)
    return member


async def get_pending_family_invites(db: AsyncSession, user_id: UUID) -> List[FamilyMember]:
    result = await db.execute(
        select(FamilyMember).where(and_(FamilyMember.user_id == user_id, FamilyMember.status == "pending"))
    )
    return list(result.scalars().all())


async def update_family_member_visibility(
    db: AsyncSession, member_id: UUID, current_user_id: UUID, updates: FamilyMemberVisibilityUpdate
) -> FamilyMember:
    result = await db.execute(select(FamilyMember).where(FamilyMember.id == member_id))
    member = result.scalars().first()
    if not member:
        raise LookupError("Family member not found")

    is_self = member.user_id == current_user_id and member.status == "accepted"
    is_head_of_placeholder = False
    if member.user_id is None:
        fam_result = await db.execute(select(Family).where(Family.id == member.family_id))
        family = fam_result.scalars().first()
        is_head_of_placeholder = bool(family and family.head_id == current_user_id)

    if not (is_self or is_head_of_placeholder):
        raise PermissionError("You can only change visibility for your own linked profile, or for members without their own account")

    if updates.visible_phone is not None:
        member.visible_phone = updates.visible_phone
    if updates.visible_kyc is not None:
        member.visible_kyc = updates.visible_kyc
    await db.commit()
    await db.refresh(member)
    return member


async def get_family(db: AsyncSession, family_id: UUID) -> Optional[Family]:
    result = await db.execute(
        select(Family).options(selectinload(Family.members)).where(Family.id == family_id)
    )
    return result.scalars().first()


async def get_user_family(db: AsyncSession, user_id: UUID) -> Optional[Family]:
    """Retrieves the family a user belongs to, as either the head or an *accepted* linked member."""
    mem_result = await db.execute(
        select(FamilyMember).where(and_(FamilyMember.user_id == user_id, FamilyMember.status == "accepted"))
    )
    member_link = mem_result.scalars().first()

    if member_link:
        fam_id = member_link.family_id
    else:
        fam_head_result = await db.execute(select(Family).where(Family.head_id == user_id))
        family = fam_head_result.scalars().first()
        if not family:
            return None
        fam_id = family.id

    return await get_family(db, fam_id)


# ===========================================================================
# Community Groups
# ===========================================================================

async def create_community_group(db: AsyncSession, creator_id: UUID, group_in: CommunityGroupCreate) -> CommunityGroup:
    group = CommunityGroup(
        name=group_in.name, group_type=group_in.group_type,
        description=group_in.description, location_geohash=group_in.location_geohash,
        created_by=creator_id,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    # Creating a group implies membership.
    db.add(CommunityGroupMember(group_id=group.id, user_id=creator_id, role="admin"))
    await db.commit()
    return await _attach_group_meta(db, [group], creator_id)[0]


async def _attach_group_meta(db: AsyncSession, groups: List[CommunityGroup], viewer_id: Optional[UUID]) -> List[CommunityGroup]:
    if not groups:
        return []
    group_ids = [g.id for g in groups]
    count_rows = await db.execute(
        select(CommunityGroupMember.group_id, func.count(CommunityGroupMember.id))
        .where(CommunityGroupMember.group_id.in_(group_ids))
        .group_by(CommunityGroupMember.group_id)
    )
    counts = dict(count_rows.all())
    member_ids = set()
    if viewer_id:
        mem_rows = await db.execute(
            select(CommunityGroupMember.group_id).where(
                and_(CommunityGroupMember.group_id.in_(group_ids), CommunityGroupMember.user_id == viewer_id)
            )
        )
        member_ids = set(mem_rows.scalars().all())
    for g in groups:
        setattr(g, "member_count", counts.get(g.id, 0))
        setattr(g, "is_member", g.id in member_ids)
    return groups


async def get_community_groups(db: AsyncSession, geohash_prefix: Optional[str] = None, viewer_id: Optional[UUID] = None) -> List[CommunityGroup]:
    db_query = select(CommunityGroup)
    if geohash_prefix:
        db_query = db_query.where(CommunityGroup.location_geohash.like(f"{geohash_prefix}%"))
    result = await db.execute(db_query)
    groups = list(result.scalars().all())
    return await _attach_group_meta(db, groups, viewer_id)


async def get_my_groups(db: AsyncSession, user_id: UUID) -> List[CommunityGroup]:
    result = await db.execute(
        select(CommunityGroup)
        .join(CommunityGroupMember, CommunityGroupMember.group_id == CommunityGroup.id)
        .where(CommunityGroupMember.user_id == user_id)
    )
    groups = list(result.scalars().all())
    return await _attach_group_meta(db, groups, user_id)


async def join_community_group(db: AsyncSession, group_id: UUID, user_id: UUID) -> CommunityGroup:
    group_result = await db.execute(select(CommunityGroup).where(CommunityGroup.id == group_id))
    group = group_result.scalars().first()
    if not group:
        raise LookupError("Community group not found")

    existing = await db.execute(
        select(CommunityGroupMember).where(
            and_(CommunityGroupMember.group_id == group_id, CommunityGroupMember.user_id == user_id)
        )
    )
    if not existing.scalars().first():
        db.add(CommunityGroupMember(group_id=group_id, user_id=user_id))
        await db.commit()
    result = await _attach_group_meta(db, [group], user_id)
    return result[0]


async def leave_community_group(db: AsyncSession, group_id: UUID, user_id: UUID) -> None:
    result = await db.execute(
        select(CommunityGroupMember).where(
            and_(CommunityGroupMember.group_id == group_id, CommunityGroupMember.user_id == user_id)
        )
    )
    membership = result.scalars().first()
    if not membership:
        raise LookupError("You aren't a member of this group")
    await db.delete(membership)
    await db.commit()


# ===========================================================================
# Matrimonial Layer
# ===========================================================================

def _calc_age(birth_date: datetime) -> int:
    today = datetime.now(timezone.utc).date()
    bd = birth_date.date() if isinstance(birth_date, datetime) else birth_date
    return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))


async def _check_matrimonial_eligibility(db: AsyncSession, user: User) -> tuple[datetime, str]:
    """
    Server-side age/identity gate. Never trusts client-submitted birthdates.
    Requires: a date of birth on the verified profile implying 18+, AND an approved KYC record.
    Re-run on every opt-in — never cached from login time.
    """
    if not user.date_of_birth:
        raise ValueError("Please add your date of birth in your profile before continuing.")
    try:
        birth_date = datetime.strptime(user.date_of_birth, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ValueError("The date of birth on your profile is invalid. Please update it before continuing.")

    if _calc_age(birth_date) < 18:
        raise ValueError("You must be 18 years or older to use the matrimonial layer.")

    kyc_result = await db.execute(
        select(KYCRecord).where(and_(KYCRecord.user_id == user.id, KYCRecord.verification_status == "approved"))
    )
    kyc = kyc_result.scalars().first()
    if not kyc:
        raise ValueError("Please complete identity (KYC) verification before opting into the matrimonial layer.")

    return birth_date, f"kyc_record:{kyc.id}"


async def _compute_family_verified_badge(db: AsyncSession, user_id: UUID, wants_badge: bool) -> bool:
    if not wants_badge:
        return False
    family = await get_user_family(db, user_id)
    if not family:
        return False
    kyc_result = await db.execute(
        select(KYCRecord).where(and_(KYCRecord.user_id == family.head_id, KYCRecord.verification_status == "approved"))
    )
    return kyc_result.scalars().first() is not None


def _profile_to_dict(profile: MatrimonialProfile, badge: bool, about: Optional[str], photo: Optional[str], my_interest_status: Optional[str]) -> Dict[str, Any]:
    return {
        "id": profile.id, "user_id": profile.user_id, "gender": profile.gender,
        "age": _calc_age(profile.birth_date), "religion": profile.religion, "caste": profile.caste,
        "occupation": profile.occupation, "education": profile.education,
        "about": about, "photo_url": photo, "status": profile.status,
        "age_verified": profile.age_verified, "family_verified_badge": badge,
        "show_verified_family_badge": profile.show_verified_family_badge,
        "opt_in_confirmed": profile.opt_in_confirmed, "my_interest_status": my_interest_status,
        "created_at": profile.created_at,
    }


async def create_matrimonial_profile(db: AsyncSession, user: User, profile_in: MatrimonialOptIn) -> Dict[str, Any]:
    if not profile_in.consent_confirmed:
        raise ValueError("Consent required: please confirm the matrimonial consent statement to proceed.")

    existing_result = await db.execute(select(MatrimonialProfile).where(MatrimonialProfile.user_id == user.id))
    existing = existing_result.scalars().first()
    if existing and existing.status != "removed":
        raise ValueError("A matrimonial profile already exists for this account")

    birth_date, source = await _check_matrimonial_eligibility(db, user)

    if existing:
        profile = existing
        profile.status = "active"
        profile.opted_out_at = None
    else:
        profile = MatrimonialProfile(user_id=user.id)
        db.add(profile)

    profile.gender = profile_in.gender
    profile.birth_date = birth_date
    profile.religion = profile_in.religion
    profile.caste = profile_in.caste
    profile.occupation = profile_in.occupation
    profile.education = profile_in.education
    profile.about = profile_in.about
    profile.photo_url = profile_in.photo_url
    profile.show_verified_family_badge = profile_in.show_verified_family_badge
    profile.opt_in_confirmed = True
    profile.age_verified = True
    profile.age_verification_source = source
    profile.opted_in_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(profile)

    badge = await _compute_family_verified_badge(db, user.id, profile.show_verified_family_badge)
    return _profile_to_dict(profile, badge, profile.about, profile.photo_url, None)


async def get_my_matrimonial_profile(db: AsyncSession, user_id: UUID) -> Optional[Dict[str, Any]]:
    result = await db.execute(select(MatrimonialProfile).where(MatrimonialProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile or profile.status == "removed":
        return None
    badge = await _compute_family_verified_badge(db, user_id, profile.show_verified_family_badge)
    return _profile_to_dict(profile, badge, profile.about, profile.photo_url, None)


async def update_matrimonial_profile(db: AsyncSession, user_id: UUID, updates: MatrimonialProfileUpdate) -> Dict[str, Any]:
    result = await db.execute(select(MatrimonialProfile).where(MatrimonialProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile or profile.status == "removed":
        raise LookupError("No matrimonial profile found. Opt in first.")
    if profile.status == "suspended":
        raise PermissionError("Your profile is suspended pending moderation review and can't be edited.")

    for field in ("religion", "caste", "occupation", "education", "about", "photo_url", "show_verified_family_badge"):
        value = getattr(updates, field)
        if value is not None:
            setattr(profile, field, value)
    if updates.status is not None:
        profile.status = updates.status

    await db.commit()
    await db.refresh(profile)
    badge = await _compute_family_verified_badge(db, user_id, profile.show_verified_family_badge)
    return _profile_to_dict(profile, badge, profile.about, profile.photo_url, None)


async def opt_out_matrimonial(db: AsyncSession, user_id: UUID) -> None:
    result = await db.execute(select(MatrimonialProfile).where(MatrimonialProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise LookupError("No matrimonial profile found")
    profile.status = "removed"
    profile.opted_out_at = datetime.now(timezone.utc)

    # Immediately clear any pending interests involving this profile so it stops appearing
    # in the other party's inbox in the same request/response cycle.
    pending_result = await db.execute(
        select(MatrimonialInterest).where(
            and_(
                or_(MatrimonialInterest.from_user_id == user_id, MatrimonialInterest.to_user_id == user_id),
                MatrimonialInterest.status == "pending",
            )
        )
    )
    for interest in pending_result.scalars().all():
        interest.status = "withdrawn"
        interest.responded_at = datetime.now(timezone.utc)

    await db.commit()


async def search_matrimonial_profiles(
    db: AsyncSession, viewer: User,
    gender: Optional[str] = None, religion: Optional[str] = None, caste: Optional[str] = None,
    occupation: Optional[str] = None, verified_only: bool = False,
    min_age: Optional[int] = None, max_age: Optional[int] = None,
) -> List[Dict[str, Any]]:
    blocked_result = await db.execute(select(UserBlock.blocked_user_id).where(UserBlock.user_id == viewer.id))
    blockers_result = await db.execute(select(UserBlock.user_id).where(UserBlock.blocked_user_id == viewer.id))
    excluded = set(blocked_result.scalars().all()) | set(blockers_result.scalars().all())
    excluded.add(viewer.id)

    q = select(MatrimonialProfile).where(
        and_(MatrimonialProfile.user_id.notin_(list(excluded)), MatrimonialProfile.status == "active")
    )
    if gender:
        q = q.where(MatrimonialProfile.gender == gender)
    if religion:
        q = q.where(MatrimonialProfile.religion.ilike(religion))
    if caste:
        q = q.where(MatrimonialProfile.caste.ilike(caste))
    if occupation:
        q = q.where(MatrimonialProfile.occupation.ilike(f"%{occupation}%"))
    if verified_only:
        q = q.where(MatrimonialProfile.show_verified_family_badge == True)  # noqa: E712

    result = await db.execute(q)
    profiles = list(result.scalars().all())
    if min_age is not None or max_age is not None:
        def _in_range(p: MatrimonialProfile) -> bool:
            age = _calc_age(p.birth_date)
            if min_age is not None and age < min_age:
                return False
            if max_age is not None and age > max_age:
                return False
            return True
        profiles = [p for p in profiles if _in_range(p)]
    if not profiles:
        return []

    # --- Batch badge computation (avoids N+1 family/KYC lookups per result) ---
    badge_candidates = [p.user_id for p in profiles if p.show_verified_family_badge]
    verified_owner_ids = set()
    if badge_candidates:
        member_rows = await db.execute(
            select(FamilyMember.user_id, FamilyMember.family_id).where(
                and_(FamilyMember.user_id.in_(badge_candidates), FamilyMember.status == "accepted")
            )
        )
        member_to_family = dict(member_rows.all())
        head_rows = await db.execute(select(Family.head_id, Family.id).where(Family.head_id.in_(badge_candidates)))
        head_family = dict(head_rows.all())
        family_ids_needed = set(member_to_family.values()) | set(head_family.values())
        heads_by_family: Dict[UUID, UUID] = {}
        if family_ids_needed:
            fam_rows = await db.execute(select(Family.id, Family.head_id).where(Family.id.in_(family_ids_needed)))
            heads_by_family = dict(fam_rows.all())
        candidate_head: Dict[UUID, Optional[UUID]] = {}
        for uid in badge_candidates:
            if uid in head_family:
                candidate_head[uid] = uid
            elif uid in member_to_family:
                candidate_head[uid] = heads_by_family.get(member_to_family[uid])
        head_ids_to_check = {v for v in candidate_head.values() if v}
        approved_heads = set()
        if head_ids_to_check:
            kyc_rows = await db.execute(
                select(KYCRecord.user_id).where(
                    and_(KYCRecord.user_id.in_(head_ids_to_check), KYCRecord.verification_status == "approved")
                )
            )
            approved_heads = set(kyc_rows.scalars().all())
        verified_owner_ids = {uid for uid, head in candidate_head.items() if head in approved_heads}

    # --- Batch interest/match status (avoids N+1 interest lookups per result) ---
    interest_rows = await db.execute(
        select(MatrimonialInterest).where(
            or_(MatrimonialInterest.from_user_id == viewer.id, MatrimonialInterest.to_user_id == viewer.id)
        )
    )
    matched_owner_ids = set()
    status_by_owner: Dict[UUID, str] = {}
    for it in interest_rows.scalars().all():
        other = it.to_user_id if it.from_user_id == viewer.id else it.from_user_id
        if it.status == "accepted":
            matched_owner_ids.add(other)
            status_by_owner[other] = "matched"
        elif it.status == "pending":
            status_by_owner.setdefault(other, "sent_pending" if it.from_user_id == viewer.id else "received_pending")
        elif it.status == "declined":
            status_by_owner.setdefault(other, "declined")

    out = []
    for p in profiles:
        is_matched = p.user_id in matched_owner_ids
        out.append(_profile_to_dict(
            p,
            badge=p.user_id in verified_owner_ids,
            about=p.about if is_matched else None,
            photo=p.photo_url if is_matched else None,
            my_interest_status=status_by_owner.get(p.user_id, "none"),
        ))
    return out


# --- Interests (connection requests) ---

async def send_interest(db: AsyncSession, from_user: User, to_user_id: UUID) -> MatrimonialInterest:
    if from_user.id == to_user_id:
        raise ValueError("You can't send interest to yourself")

    sender_result = await db.execute(
        select(MatrimonialProfile).where(and_(MatrimonialProfile.user_id == from_user.id, MatrimonialProfile.status == "active"))
    )
    if not sender_result.scalars().first():
        raise PermissionError("Create and activate your matrimonial profile before sending interest")

    target_result = await db.execute(
        select(MatrimonialProfile).where(and_(MatrimonialProfile.user_id == to_user_id, MatrimonialProfile.status == "active"))
    )
    if not target_result.scalars().first():
        raise LookupError("This profile is not available")

    blocked_result = await db.execute(
        select(UserBlock).where(
            or_(
                and_(UserBlock.user_id == from_user.id, UserBlock.blocked_user_id == to_user_id),
                and_(UserBlock.user_id == to_user_id, UserBlock.blocked_user_id == from_user.id),
            )
        )
    )
    if blocked_result.scalars().first():
        raise PermissionError("You can't contact this profile")

    dup_result = await db.execute(
        select(MatrimonialInterest).where(
            and_(
                MatrimonialInterest.from_user_id == from_user.id,
                MatrimonialInterest.to_user_id == to_user_id,
                MatrimonialInterest.status == "pending",
            )
        )
    )
    if dup_result.scalars().first():
        raise ValueError("You've already sent interest to this profile")

    since_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    count_result = await db.execute(
        select(func.count(MatrimonialInterest.id)).where(
            and_(MatrimonialInterest.from_user_id == from_user.id, MatrimonialInterest.created_at >= since_midnight)
        )
    )
    if (count_result.scalar() or 0) >= DAILY_INTEREST_LIMIT:
        raise ValueError(f"Daily interest limit reached ({DAILY_INTEREST_LIMIT}/day). Please try again tomorrow.")

    interest = MatrimonialInterest(from_user_id=from_user.id, to_user_id=to_user_id, status="pending")
    db.add(interest)
    await db.commit()
    await db.refresh(interest)
    return interest


async def respond_to_interest(db: AsyncSession, current_user_id: UUID, interest_id: UUID, action: str) -> MatrimonialInterest:
    result = await db.execute(select(MatrimonialInterest).where(MatrimonialInterest.id == interest_id))
    interest = result.scalars().first()
    if not interest:
        raise LookupError("Interest not found")

    if action == "withdraw":
        if interest.from_user_id != current_user_id:
            raise PermissionError("Only the sender can withdraw this interest")
        if interest.status != "pending":
            raise ValueError("Only a pending interest can be withdrawn")
        interest.status = "withdrawn"
    else:
        if interest.to_user_id != current_user_id:
            raise PermissionError("Only the recipient can respond to this interest")
        if interest.status != "pending":
            raise ValueError("This interest has already been responded to")
        interest.status = "accepted" if action == "accept" else "declined"

    interest.responded_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(interest)
    return interest


async def get_my_interests(db: AsyncSession, user_id: UUID, direction: str) -> List[Dict[str, Any]]:
    if direction == "sent":
        q = select(MatrimonialInterest).where(MatrimonialInterest.from_user_id == user_id)
    else:
        q = select(MatrimonialInterest).where(MatrimonialInterest.to_user_id == user_id)
    result = await db.execute(q.order_by(MatrimonialInterest.created_at.desc()))
    interests = list(result.scalars().all())
    if not interests:
        return []

    counterpart_ids = [
        (it.to_user_id if it.from_user_id == user_id else it.from_user_id) for it in interests
    ]
    profiles_result = await db.execute(select(MatrimonialProfile).where(MatrimonialProfile.user_id.in_(counterpart_ids)))
    profiles_by_user = {p.user_id: p for p in profiles_result.scalars().all()}

    # Badges for counterpart profiles (small list — simple per-item is fine here).
    out = []
    for it in interests:
        counterpart_id = it.to_user_id if it.from_user_id == user_id else it.from_user_id
        profile = profiles_by_user.get(counterpart_id)
        counterpart_dict = None
        if profile:
            is_matched = it.status == "accepted"
            badge = await _compute_family_verified_badge(db, counterpart_id, profile.show_verified_family_badge)
            counterpart_dict = _profile_to_dict(
                profile, badge,
                about=profile.about if is_matched else None,
                photo=profile.photo_url if is_matched else None,
                my_interest_status=it.status,
            )
        out.append({
            "id": it.id, "from_user_id": it.from_user_id, "to_user_id": it.to_user_id,
            "status": it.status, "created_at": it.created_at, "responded_at": it.responded_at,
            "counterpart_profile": counterpart_dict,
        })
    return out


# ===========================================================================
# Safety: Blocking & Abuse Reporting
# ===========================================================================

async def block_user(db: AsyncSession, user_id: UUID, blocked_user_id: UUID) -> UserBlock:
    if user_id == blocked_user_id:
        raise ValueError("You cannot block yourself")

    exists_result = await db.execute(
        select(UserBlock).where(and_(UserBlock.user_id == user_id, UserBlock.blocked_user_id == blocked_user_id))
    )
    existing = exists_result.scalars().first()
    if existing:
        return existing

    block = UserBlock(user_id=user_id, blocked_user_id=blocked_user_id)
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return block


async def unblock_user(db: AsyncSession, user_id: UUID, blocked_user_id: UUID) -> None:
    result = await db.execute(
        select(UserBlock).where(and_(UserBlock.user_id == user_id, UserBlock.blocked_user_id == blocked_user_id))
    )
    block = result.scalars().first()
    if block:
        await db.delete(block)
        await db.commit()


async def get_blocked_users(db: AsyncSession, user_id: UUID) -> List[UserBlock]:
    result = await db.execute(select(UserBlock).where(UserBlock.user_id == user_id))
    return list(result.scalars().all())


async def submit_user_report(db: AsyncSession, reporter_id: UUID, report_in: UserReportCreate) -> UserReport:
    if reporter_id == report_in.reported_user_id:
        raise ValueError("You cannot report yourself")

    report = UserReport(
        reporter_id=reporter_id,
        reported_user_id=report_in.reported_user_id,
        reason_code=report_in.reason_code,
        details=report_in.details,
        status="open",
    )
    db.add(report)

    if report_in.reason_code == "underage_suspicion":
        # Bypass the normal moderation SLA: suspend on receipt, don't wait for review.
        profile_result = await db.execute(
            select(MatrimonialProfile).where(MatrimonialProfile.user_id == report_in.reported_user_id)
        )
        profile = profile_result.scalars().first()
        if profile and profile.status != "removed":
            profile.status = "suspended"
        report.status = "reviewing"

    await db.commit()
    await db.refresh(report)
    return report


# ===========================================================================
# Admin Moderation
# ===========================================================================

async def list_reports(db: AsyncSession, status_filter: Optional[str] = None, reason_code_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    q = select(UserReport)
    if status_filter:
        q = q.where(UserReport.status == status_filter)
    if reason_code_filter:
        q = q.where(UserReport.reason_code == reason_code_filter)
    q = q.order_by(UserReport.created_at.desc())
    result = await db.execute(q)
    reports = list(result.scalars().all())
    if not reports:
        return []

    reported_ids = list({r.reported_user_id for r in reports})
    profiles_result = await db.execute(select(MatrimonialProfile).where(MatrimonialProfile.user_id.in_(reported_ids)))
    profiles_by_user = {p.user_id: p for p in profiles_result.scalars().all()}

    count_rows = await db.execute(
        select(UserReport.reported_user_id, func.count(UserReport.id))
        .where(UserReport.reported_user_id.in_(reported_ids))
        .group_by(UserReport.reported_user_id)
    )
    counts = dict(count_rows.all())

    out = []
    for r in reports:
        p = profiles_by_user.get(r.reported_user_id)
        out.append({
            "id": r.id, "reporter_id": r.reporter_id, "reported_user_id": r.reported_user_id,
            "reason_code": r.reason_code, "details": r.details, "status": r.status,
            "created_at": r.created_at, "resolved_at": r.resolved_at, "resolution_action": r.resolution_action,
            "reported_profile_status": p.status if p else None,
            "reported_profile_age_verified": p.age_verified if p else None,
            "report_count_against_user": counts.get(r.reported_user_id, 0),
        })
    return out


async def resolve_report(db: AsyncSession, admin_id: UUID, report_id: UUID, action: str, note: Optional[str]) -> UserReport:
    result = await db.execute(select(UserReport).where(UserReport.id == report_id))
    report = result.scalars().first()
    if not report:
        raise LookupError("Report not found")

    report.status = "dismissed" if action == "dismiss" else "actioned"
    report.resolved_at = datetime.now(timezone.utc)
    report.resolved_by = admin_id
    report.resolution_action = action
    if note:
        report.details = f"{report.details or ''}\n[admin note] {note}".strip()

    if action in ("suspend_profile", "remove_profile", "reinstate_profile"):
        profile_result = await db.execute(
            select(MatrimonialProfile).where(MatrimonialProfile.user_id == report.reported_user_id)
        )
        profile = profile_result.scalars().first()
        if profile:
            if action == "suspend_profile":
                profile.status = "suspended"
            elif action == "remove_profile":
                profile.status = "removed"
                profile.opted_out_at = datetime.now(timezone.utc)
            elif action == "reinstate_profile":
                profile.status = "active"

    await db.commit()
    await db.refresh(report)
    return report
