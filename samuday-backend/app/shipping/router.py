from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.identity.models import User
from app.marketplace.models import Listing, Order
from app.shipping import service, delhivery_client
from app.shipping.schemas import (
    DispatchProfileCreate, DispatchProfileResponse, ShipmentResponse,
    ShippingRateRequest, ShippingRateResponse,
)

router = APIRouter(prefix="/shipping", tags=["Shipping & Delhivery"])

@router.get("/status")
async def get_shipping_integration_status():
    """Public: whether a real Delhivery account is connected, or the platform is running in simulated mode."""
    return {"delhivery_connected": delhivery_client.is_delhivery_connected()}

@router.get("/dispatch-profile", response_model=DispatchProfileResponse)
async def get_my_dispatch_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns the current seller's pickup/dispatch info, if set up."""
    profile = await service.get_dispatch_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch profile not set up yet.")
    return profile

@router.put("/dispatch-profile", response_model=DispatchProfileResponse)
async def upsert_my_dispatch_profile(
    payload: DispatchProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Creates or updates the current seller's pickup/dispatch info, required before courier fulfillment works for their listings."""
    return await service.upsert_dispatch_profile(db, current_user.id, payload)

@router.post("/rate", response_model=ShippingRateResponse)
async def calculate_rate_endpoint(
    payload: ShippingRateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Estimates the delivery fee for a listing to a destination pincode (used at checkout before an address is finalized)."""
    result = await db.execute(select(Listing).where(Listing.id == payload.listing_id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")

    dispatch_profile = await service.get_dispatch_profile(db, listing.seller_id)
    if not dispatch_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seller has not set up pickup/dispatch information yet.")

    weight_grams = (listing.weight_grams or service.DEFAULT_ITEM_WEIGHT_GRAMS) * payload.quantity
    rate = await service.calculate_delivery_fee(weight_grams, dispatch_profile.pickup_pincode, payload.destination_pincode)
    return ShippingRateResponse(delivery_fee_paise=rate["amount_paise"], is_simulated=rate["is_simulated"])

@router.get("/track/{order_id}", response_model=ShipmentResponse)
async def track_order_shipment(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns live tracking info for an order's shipment. Buyer or seller of the order only."""
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalars().first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if current_user.id not in (order.buyer_id, order.seller_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this shipment.")

    shipment = await service.get_shipment_for_order(db, order_id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No shipment found for this order.")

    shipment = await service.refresh_tracking_status(db, shipment)
    return shipment
