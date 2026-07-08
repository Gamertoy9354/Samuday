import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class SupplierProfile(Base):
    __tablename__ = "supplier_profiles"
    __table_args__ = {"schema": "enterprise"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    business_name = Column(String, nullable=False)
    gstin = Column(String, nullable=False)  # GST identification number
    is_verified = Column(Boolean, default=False, nullable=False)
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
