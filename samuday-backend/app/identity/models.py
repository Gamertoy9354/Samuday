import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "identity"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Encrypted phone number (for display/contact)
    phone_number = Column(String, nullable=True)
    # SHA-256 hash of the phone number (for lookup/uniqueness)
    phone_number_hash = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    avatar_url = Column(String, nullable=True)
    google_id = Column(String, unique=True, index=True, nullable=True)
    is_seller = Column(Boolean, default=False, nullable=False)
    profile_bio = Column(String, nullable=True)
    preferred_language = Column(String, default="en", nullable=False)
    status = Column(String, default="active", nullable=False)  # active, suspended
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    kyc_records = relationship("KYCRecord", back_populates="user", cascade="all, delete-orphan")
    reputation_scores = relationship("ReputationScore", back_populates="user", cascade="all, delete-orphan")

class KYCRecord(Base):
    __tablename__ = "kyc_records"
    __table_args__ = {"schema": "identity"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    id_type = Column(String, nullable=False)  # aadhaar, pan, voter_id
    document_url = Column(String, nullable=False)  # encrypted document key reference
    verification_status = Column(String, default="pending", nullable=False)  # pending, approved, rejected
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="kyc_records")

class ReputationScore(Base):
    __tablename__ = "reputation_scores"
    __table_args__ = {"schema": "identity"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    pillar = Column(String, default="aggregate", nullable=False)  # aggregate, sheshop, kisan, etc.
    score = Column(Float, default=5.0, nullable=False)
    total_transactions = Column(Integer, default=0, nullable=False)
    positive_count = Column(Integer, default=0, nullable=False)
    negative_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="reputation_scores")

class Vouch(Base):
    __tablename__ = "vouches"
    __table_args__ = (
        UniqueConstraint("voucher_user_id", "vouched_user_id", "pillar", name="uq_vouch"),
        {"schema": "identity"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    voucher_user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    vouched_user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    pillar = Column(String, default="general", nullable=False)  # sheshop, kisan, general
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
