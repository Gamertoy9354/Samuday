import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shipping.models import SellerDispatchProfile, Shipment
from app.shipping.schemas import DispatchProfileCreate
from app.shipping import delhivery_client

logger = logging.getLogger(__name__)

DEFAULT_ITEM_WEIGHT_GRAMS = 500  # fallback when a listing has no weight set


async def get_dispatch_profile(db: AsyncSession, seller_id: UUID) -> Optional[SellerDispatchProfile]:
    result = await db.execute(select(SellerDispatchProfile).where(SellerDispatchProfile.seller_id == seller_id))
    return result.scalars().first()


async def upsert_dispatch_profile(db: AsyncSession, seller_id: UUID, payload: DispatchProfileCreate) -> SellerDispatchProfile:
    profile = await get_dispatch_profile(db, seller_id)
    if profile:
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)
        profile.updated_at = datetime.now(timezone.utc)
    else:
        profile = SellerDispatchProfile(seller_id=seller_id, **payload.model_dump())
        db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def calculate_delivery_fee(weight_grams: int, origin_pincode: str, destination_pincode: str) -> dict:
    """Thin wrapper around the Delhivery client's rate calculator."""
    return await delhivery_client.calculate_shipping_rate(weight_grams, origin_pincode, destination_pincode)


async def create_order_shipment(
    db: AsyncSession,
    order_id: UUID,
    dispatch_profile: SellerDispatchProfile,
    destination_pincode: str,
    consignee: dict,  # {name, address, city, state, pincode, phone}
    weight_grams: int,
    delivery_fee_paise: int,
    total_amount_paise: int,
) -> Shipment:
    """Creates the Shipment record and attempts real Delhivery manifestation if connected."""
    pickup = {
        "name": dispatch_profile.delhivery_client_name or dispatch_profile.contact_name,
        "address": dispatch_profile.pickup_address_line1,
        "city": dispatch_profile.pickup_city,
        "state": dispatch_profile.pickup_state,
        "pincode": dispatch_profile.pickup_pincode,
        "phone": dispatch_profile.contact_phone,
    }
    result = await delhivery_client.create_shipment(
        order_id=order_id,
        pickup=pickup,
        consignee=consignee,
        weight_grams=weight_grams,
        total_amount_paise=total_amount_paise,
    )

    shipment = Shipment(
        order_id=order_id,
        waybill_number=result["waybill_number"],
        courier_status="manifested" if result["waybill_number"] else "pending",
        tracking_url=result["tracking_url"],
        origin_pincode=dispatch_profile.pickup_pincode,
        destination_pincode=destination_pincode,
        weight_grams=weight_grams,
        delivery_fee_paise=delivery_fee_paise,
        estimated_delivery_date=datetime.now(timezone.utc) + timedelta(days=5),
        is_simulated=result["is_simulated"],
    )
    db.add(shipment)
    await db.flush()
    return shipment


async def get_shipment_for_order(db: AsyncSession, order_id: UUID) -> Optional[Shipment]:
    result = await db.execute(select(Shipment).where(Shipment.order_id == order_id))
    return result.scalars().first()


async def refresh_tracking_status(db: AsyncSession, shipment: Shipment) -> Shipment:
    """Pulls the latest status from Delhivery for a real (non-simulated) shipment."""
    if shipment.is_simulated or not shipment.waybill_number:
        return shipment
    status = await delhivery_client.get_tracking_status(shipment.waybill_number)
    if status and status.get("status"):
        shipment.courier_status = status["status"]
        shipment.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(shipment)
    return shipment
