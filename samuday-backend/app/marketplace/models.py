import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, BigInteger, Integer, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    pillar = Column(String, nullable=False)  # marketplace, sheshop, kisan, etc.
    icon_url = Column(String, nullable=True)

    listings = relationship("Listing", back_populates="category")

class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pillar = Column(String, nullable=False)  # marketplace, sheshop, kisan
    category_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.categories.id", ondelete="RESTRICT"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price = Column(BigInteger, nullable=False)  # in paise
    listing_type = Column(String, nullable=False)  # sale, rent, service, crop, equipment
    quantity = Column(Integer, default=1, nullable=False)
    unit = Column(String, nullable=True)  # kg, piece, hours, etc.
    location_geohash = Column(String, index=True, nullable=True)
    status = Column(String, default="active", nullable=False)  # active, sold, suspended
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    category = relationship("Category", back_populates="listings")
    media = relationship("ListingMedia", back_populates="listing", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="listing")

class ListingMedia(Base):
    __tablename__ = "listing_media"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.listings.id", ondelete="CASCADE"), nullable=False)
    media_url = Column(String, nullable=False)
    media_type = Column(String, default="image", nullable=False)  # image, video
    sort_order = Column(Integer, default=0, nullable=False)

    listing = relationship("Listing", back_populates="media")

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    seller_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.listings.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    total_amount = Column(BigInteger, nullable=False)  # in paise
    status = Column(String, default="pending", nullable=False)  # pending, paid, shipped, completed, cancelled, refunded
    fulfillment_type = Column(String, default="self_pickup", nullable=False)  # self_pickup, seller_delivery, courier
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    listing = relationship("Listing", back_populates="orders")
    reviews = relationship("Review", back_populates="order", cascade="all, delete-orphan")

class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.listings.id", ondelete="RESTRICT"), nullable=False)
    slot_start = Column(DateTime(timezone=True), nullable=False)
    slot_end = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, confirmed, completed, cancelled

class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.orders.id", ondelete="CASCADE"), nullable=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.bookings.id", ondelete="CASCADE"), nullable=True)
    reviewer_id = Column(UUID(as_uuid=True), nullable=False)
    reviewee_id = Column(UUID(as_uuid=True), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5 stars
    comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    order = relationship("Order", back_populates="reviews")

class Chat(Base):
    __tablename__ = "chats"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.listings.id", ondelete="SET NULL"), nullable=True)
    buyer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    seller_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.chats.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), nullable=False)
    content = Column(String, nullable=False)
    translated_content = Column(String, nullable=True)  # auto-translated result
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    chat = relationship("Chat", back_populates="messages")
