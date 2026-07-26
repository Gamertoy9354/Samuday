import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, DateTime, Date, ForeignKey, BigInteger, Integer, Float, Boolean, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        Index(
            "ix_categories_name_trgm", "name",
            postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}
        ),
        {"schema": "marketplace"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    pillar = Column(String, nullable=False)  # marketplace, sheshop, kisan, etc.
    icon_url = Column(String, nullable=True)

    listings = relationship("Listing", back_populates="category")

class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        Index("ix_listings_status_pillar_category", "status", "pillar", "category_id"),
        Index("ix_listings_created_at", "created_at"),
        Index(
            "ix_listings_title_trgm", "title",
            postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}
        ),
        Index(
            "ix_listings_description_trgm", "description",
            postgresql_using="gin", postgresql_ops={"description": "gin_trgm_ops"}
        ),
        {"schema": "marketplace"},
    )

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
    status = Column(String, default="active", nullable=False)  # active, sold, suspended, paused, removed
    # Shipping attributes, used for Delhivery rate calculation at checkout
    weight_grams = Column(Integer, nullable=True)
    length_cm = Column(Integer, nullable=True)
    width_cm = Column(Integer, nullable=True)
    height_cm = Column(Integer, nullable=True)
    # JSON array of seller-entered offer strings (e.g. bank/card offers), shown on the PDP.
    available_offers_json = Column("available_offers", Text, nullable=True)
    return_policy = Column(Text, nullable=True)
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

class JobListing(Base):
    """1:1 extension of a Jobs-category Listing — salary/employment details that don't fit the generic product schema."""
    __tablename__ = "job_listings"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.listings.id", ondelete="CASCADE"), nullable=False, unique=True)
    job_type = Column(String, nullable=False)  # full-time, part-time, contract, internship, gig
    salary_min = Column(BigInteger, nullable=True)  # paise
    salary_max = Column(BigInteger, nullable=True)  # paise
    salary_period = Column(String, nullable=True)  # monthly, yearly, hourly
    experience_required = Column(String, nullable=True)
    openings = Column(Integer, default=1, nullable=False)
    application_deadline = Column(DateTime(timezone=True), nullable=True)
    contact_email = Column(String, nullable=True)

    listing = relationship("Listing", backref="job_details_row")

class JobApplication(Base):
    """A buyer's application to a Jobs-category listing — replaces Order/CartItem for the Jobs flow."""
    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint("listing_id", "applicant_id", name="uq_job_application_listing_applicant"),
        {"schema": "marketplace"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.listings.id", ondelete="CASCADE"), nullable=False, index=True)
    applicant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    message = Column(Text, nullable=True)
    status = Column(String, default="submitted", nullable=False)  # submitted, viewed, shortlisted, rejected
    applied_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class AgriListing(Base):
    """1:1 extension of an Agriculture-category Listing — crop/produce details for a mandi-style listing."""
    __tablename__ = "agri_listings"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.listings.id", ondelete="CASCADE"), nullable=False, unique=True)
    crop_type = Column(String, nullable=True)
    is_organic = Column(Boolean, default=False, nullable=False)
    harvest_date = Column(Date, nullable=True)
    grade = Column(String, nullable=True)  # e.g. A / Premium, B / Standard, C / Economy

    listing = relationship("Listing", backref="agri_details_row")

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    seller_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.listings.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    # total_amount is the full amount charged/escrowed from the buyer:
    # product_amount + platform_fee_amount + delivery_fee_amount.
    total_amount = Column(BigInteger, nullable=False)  # in paise
    product_amount = Column(BigInteger, nullable=False, default=0)  # what the seller is paid out
    platform_fee_amount = Column(BigInteger, nullable=False, default=0)  # Samuday's cut (credited to house wallet)
    delivery_fee_amount = Column(BigInteger, nullable=False, default=0)  # passed through to courier, not credited anywhere
    gateway_fee_estimate = Column(BigInteger, nullable=False, default=0)  # informational only, no gateway connected yet
    status = Column(String, default="pending", nullable=False)  # pending, paid, shipped, completed, cancelled, refunded
    fulfillment_type = Column(String, default="self_pickup", nullable=False)  # self_pickup, seller_delivery, courier
    delivery_address_id = Column(UUID(as_uuid=True), ForeignKey("marketplace.addresses.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    listing = relationship("Listing", back_populates="orders")
    reviews = relationship("Review", back_populates="order", cascade="all, delete-orphan")

class Address(Base):
    """A buyer's saved delivery address."""
    __tablename__ = "addresses"
    __table_args__ = {"schema": "marketplace"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    label = Column(String, default="Home", nullable=False)  # Home, Work, Other
    recipient_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    address_line1 = Column(String, nullable=False)
    address_line2 = Column(String, nullable=True)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    pincode = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

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
    seller_reply = Column(Text, nullable=True)
    seller_replied_at = Column(DateTime(timezone=True), nullable=True)
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
