import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, BigInteger, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class SellerDispatchProfile(Base):
    """
    A seller's pickup/warehouse info, required by Delhivery to schedule pickups.
    One per seller. Both Official and Local marketplace sellers need one before
    their listings can be ordered with courier fulfillment.
    """
    __tablename__ = "seller_dispatch_profiles"
    __table_args__ = {"schema": "shipping"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    contact_name = Column(String, nullable=False)
    contact_phone = Column(String, nullable=False)
    pickup_address_line1 = Column(String, nullable=False)
    pickup_address_line2 = Column(String, nullable=True)
    pickup_city = Column(String, nullable=False)
    pickup_state = Column(String, nullable=False)
    pickup_pincode = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    # Delhivery "client" / warehouse name registered on their side — only meaningful
    # once the seller (or platform) has a real Delhivery account. Null = not yet connected.
    delhivery_client_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

class Shipment(Base):
    """
    Tracks courier fulfillment for one order. is_simulated=True means no real
    Delhivery account is connected yet and all figures/status are estimates —
    surfaced to sellers/admins so nobody mistakes it for a real, trackable shipment.
    """
    __tablename__ = "shipments"
    __table_args__ = {"schema": "shipping"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    waybill_number = Column(String, nullable=True, index=True)  # null until a real Delhivery shipment is created
    courier_status = Column(String, default="pending", nullable=False)
    # pending, manifested, picked_up, in_transit, out_for_delivery, delivered, rto, failed
    tracking_url = Column(String, nullable=True)
    origin_pincode = Column(String, nullable=False)
    destination_pincode = Column(String, nullable=False)
    weight_grams = Column(Integer, nullable=False)
    delivery_fee_paise = Column(BigInteger, nullable=False)
    estimated_delivery_date = Column(DateTime(timezone=True), nullable=True)
    is_simulated = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
