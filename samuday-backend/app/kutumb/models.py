import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from app.core.database import Base

class Family(Base):
    __tablename__ = "families"
    __table_args__ = {"schema": "kutumb"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)  # e.g., "Patel Family"
    head_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # User ID of family head
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class FamilyMember(Base):
    __tablename__ = "family_members"
    __table_args__ = {"schema": "kutumb"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("kutumb.families.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Nullable if the relative isn't registered on the app yet
    relationship_type = Column(String, nullable=False)  # spouse, child, parent, sibling, etc.
    display_name = Column(String, nullable=False)
    visible_phone = Column(Boolean, default=False, nullable=False)
    visible_kyc = Column(Boolean, default=False, nullable=False)
    # accepted: no account (placeholder) or the linked account holder has confirmed the link.
    # pending: a user_id was supplied but that account holder hasn't confirmed yet.
    # declined: the linked account holder rejected the link.
    status = Column(String, default="accepted", nullable=False)
    added_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)

    family = relationship("Family", backref=backref("members", cascade="all, delete-orphan"))

class CommunityGroup(Base):
    __tablename__ = "community_groups"
    __table_args__ = {"schema": "kutumb"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    group_type = Column(String, nullable=False)  # neighborhood, temple, society, etc.
    description = Column(String, nullable=False)
    location_geohash = Column(String, nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class CommunityGroupMember(Base):
    __tablename__ = "community_group_members"
    __table_args__ = {"schema": "kutumb"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("kutumb.community_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String, default="member", nullable=False)  # member, admin
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class MatrimonialProfile(Base):
    __tablename__ = "matrimonial_profiles"
    __table_args__ = {"schema": "kutumb"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    gender = Column(String, nullable=False)  # male, female, other
    birth_date = Column(DateTime(timezone=True), nullable=False)  # copied server-side from the verified identity profile, never from client input
    religion = Column(String, nullable=False)
    caste = Column(String, nullable=True)
    occupation = Column(String, nullable=False)
    education = Column(String, nullable=False)
    about = Column(Text, nullable=True)
    photo_url = Column(String, nullable=True)  # only revealed to accepted (mutual) interests
    # active: visible in discovery. paused: hidden by user choice, can be reactivated.
    # removed: opted out, permanently excluded. suspended: moderation hold (e.g. underage-suspicion report).
    status = Column(String, default="active", nullable=False)
    # Set to True only by the server-side eligibility check at opt-in time (approved KYC + verified 18+ age). Never client-settable.
    age_verified = Column(Boolean, default=False, nullable=False)
    age_verification_source = Column(String, nullable=True)  # e.g. "kyc_record:<id>"
    # User-controlled intent to show the badge; actual display also re-checks live family/KYC state at read time.
    show_verified_family_badge = Column(Boolean, default=False, nullable=False)
    opt_in_confirmed = Column(Boolean, default=False, nullable=False)  # Must be explicitly set to True by the user
    consent_version = Column(String, default="kutumb-matrimonial-consent-v1", nullable=False)
    opted_in_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    opted_out_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

class MatrimonialInterest(Base):
    __tablename__ = "matrimonial_interests"
    __table_args__ = {"schema": "kutumb"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    to_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String, default="pending", nullable=False)  # pending, accepted, declined, withdrawn
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)

class UserBlock(Base):
    __tablename__ = "user_blocks"
    __table_args__ = {"schema": "kutumb"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Blocker
    blocked_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Blocked
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class UserReport(Base):
    __tablename__ = "user_reports"
    __table_args__ = {"schema": "kutumb"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    reported_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    reason_code = Column(String, default="other", nullable=False)  # harassment, fake_profile, inappropriate_content, underage_suspicion, other
    details = Column(Text, nullable=True)
    status = Column(String, default="open", nullable=False)  # open, reviewing, actioned, dismissed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), nullable=True)
    resolution_action = Column(String, nullable=True)  # dismissed, suspended_profile, reinstated_profile, removed_profile
