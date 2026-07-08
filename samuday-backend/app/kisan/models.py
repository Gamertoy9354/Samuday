import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from app.core.database import Base

class CropListing(Base):
    __tablename__ = "crop_listings"
    __table_args__ = {"schema": "kisan"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.listings.id", ondelete="CASCADE"), unique=True, nullable=False)
    crop_type = Column(String, nullable=False)  # wheat, cotton, rice, etc.
    grade = Column(String, nullable=False)  # grade A, grade B, etc.
    harvest_date = Column(DateTime(timezone=True), nullable=False)
    mandi_price_reference = Column(BigInteger, nullable=True)  # in paise

    listing = relationship("Listing", backref=backref("crop_details", uselist=False))

class EquipmentListing(Base):
    __tablename__ = "equipment_listings"
    __table_args__ = {"schema": "kisan"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.listings.id", ondelete="CASCADE"), unique=True, nullable=False)
    equipment_type = Column(String, nullable=False)  # tractor, thresher, harvester
    rental_unit = Column(String, nullable=False)  # per_hour, per_acre, per_day
    operator_included = Column(Boolean, default=False, nullable=False)

    listing = relationship("Listing", backref=backref("equipment_details", uselist=False))

class LoanApplication(Base):
    __tablename__ = "loan_applications"
    __table_args__ = {"schema": "kisan"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    amount_requested = Column(BigInteger, nullable=False)  # in paise
    purpose = Column(String, nullable=False)
    lender_partner_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, approved, rejected
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class AdvisorySession(Base):
    __tablename__ = "advisory_sessions"
    __table_args__ = {"schema": "kisan"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    query_text = Column(String, nullable=False)
    response_text = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
