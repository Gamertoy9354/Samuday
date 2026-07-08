import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from app.core.database import Base

class ServiceProvider(Base):
    __tablename__ = "service_providers"
    __table_args__ = {"schema": "seva"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    provider_type = Column(String, nullable=False)  # free, subsidized, for_profit
    category = Column(String, nullable=False)  # medical, legal, food, education, ngo, general
    location_geohash = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class ProviderCredential(Base):
    __tablename__ = "provider_credentials"
    __table_args__ = {"schema": "seva"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("seva.service_providers.id", ondelete="CASCADE"), nullable=False)
    license_number = Column(String, nullable=False)  # Encrypted at rest (PII)
    credential_type = Column(String, nullable=False)  # medical, legal, NGO, social_work
    document_url = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, approved, rejected
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    provider = relationship("ServiceProvider", backref=backref("credentials", cascade="all, delete-orphan"))

class SevaReview(Base):
    __tablename__ = "seva_reviews"
    __table_args__ = {"schema": "seva"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("seva.service_providers.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5 stars
    comment = Column(String, nullable=True)
    verified_outcome = Column(Boolean, nullable=True)  # separate field from star rating (did it solve the problem?)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    provider = relationship("ServiceProvider", backref=backref("reviews", cascade="all, delete-orphan"))
