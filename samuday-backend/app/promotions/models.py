import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, BigInteger, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class SaleEvent(Base):
    __tablename__ = "sale_events"
    __table_args__ = {"schema": "promotions"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    banner_image_url = Column(String, nullable=True)
    discount_percent = Column(Integer, default=0, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    listing_ids_json = Column(Text, nullable=True)  # JSON array of listing UUIDs; empty/null = all of the seller's listings
    overrides_json = Column(Text, nullable=True)  # JSON dict of {listing_id: discount_percent} overrides
    status = Column(String, default="active", nullable=False)  # active, ended, cancelled
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class Advertisement(Base):
    __tablename__ = "advertisements"
    __table_args__ = {"schema": "promotions"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    image_url = Column(String, nullable=False)
    link_url = Column(String, nullable=True)  # URL to redirect on click
    listing_id = Column(UUID(as_uuid=True), nullable=True)  # the product this ad advertises
    ai_generated = Column(Boolean, default=False, nullable=False)
    placement = Column(String, default="hero_banner", nullable=False)  # hero_banner, sidebar, category_strip
    cost_paise = Column(BigInteger, default=0, nullable=False)
    status = Column(String, default="active", nullable=False)  # pending, active, expired
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    impressions = Column(Integer, default=0, nullable=False)
    clicks = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
