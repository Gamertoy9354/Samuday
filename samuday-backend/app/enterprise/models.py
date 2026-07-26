import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class SupplierProfile(Base):
    """Official-tier seller business verification (registered business, GSTIN/PAN)."""
    __tablename__ = "supplier_profiles"
    __table_args__ = {"schema": "enterprise"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    business_name = Column(String, nullable=False)
    gstin = Column(String, nullable=False)  # GST identification number
    # Nullable at the DB level (existing rows predate this field); required for new
    # submissions via SupplierProfileCreate.gst_certificate_url.
    gst_certificate_url = Column(String, nullable=True)
    pan = Column(String, nullable=True)
    business_phone = Column(String, nullable=True)
    business_address = Column(String, nullable=True)
    pincode = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)  # kept for backward compat; derive from verification_status
    verification_status = Column(String, default="pending", nullable=False)  # pending, approved, rejected
    rejection_reason = Column(String, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "enterprise"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type = Column(String, nullable=False)  # kyc_submission, wallet_credit, credential_approval, listing_deletion
    actor_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # User performing the action
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # ID of modified entity
    metadata_json = Column(String, nullable=True)  # JSON-formatted string details
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
