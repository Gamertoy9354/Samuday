import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

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

class MatrimonialProfile(Base):
    __tablename__ = "matrimonial_profiles"
    __table_args__ = {"schema": "kutumb"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    gender = Column(String, nullable=False)  # male, female, other
    birth_date = Column(DateTime(timezone=True), nullable=False)
    religion = Column(String, nullable=False)
    caste = Column(String, nullable=True)
    occupation = Column(String, nullable=False)
    education = Column(String, nullable=False)
    family_verified_badge = Column(Boolean, default=False, nullable=False)  # True if family registry is validated & head is KYC-approved
    opt_in_confirmed = Column(Boolean, default=False, nullable=False)  # Must be explicitly set to True by the user
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

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
    reason = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, reviewed, resolved
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
