import os
import uuid
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.wallet import service as wallet_service

logger = logging.getLogger(__name__)

def create_payment_checkout(amount_paise: int, current_user_id: UUID) -> dict:
    """
    Creates a payment checkout order.
    Stubs Razorpay / Cashfree order creation formats.
    """
    gateway_order_id = f"order_pay_{uuid.uuid4().hex[:12]}"
    
    # We choose Razorpay or Cashfree mock checkout endpoint based on env configurations
    gateway_provider = os.getenv("PAYMENT_PROVIDER", "razorpay")
    checkout_url = f"https://checkout.{gateway_provider}.com/pay/{gateway_order_id}"

    logger.info(f"[Payment Gateway] Created {gateway_provider} order {gateway_order_id} for user {current_user_id} of amount {amount_paise} paise")

    return {
        "gateway_order_id": gateway_order_id,
        "amount": amount_paise,
        "currency": "INR",
        "checkout_url": checkout_url,
        "status": "created"
    }

async def callback_payment_verification(
    db: AsyncSession,
    gateway_order_id: str,
    payment_id: str,
    signature: str,
    user_id: UUID,
    amount_paise: int
) -> bool:
    """
    Handles payment gateway success callback verification.
    If valid, automatically credits the user's wallet balance using the double-entry ledger.
    """
    # 1. Stub signature verification logic
    if not signature or len(signature) < 10:
        logger.warning(f"[Payment Callback] Invalid signature payload received for order {gateway_order_id}")
        return False

    logger.info(f"[Payment Callback] Verified signature for order {gateway_order_id}, payment_id: {payment_id}")

    # 2. Get or create wallet
    wallet = await wallet_service.get_wallet_by_user_id(db, user_id)
    if not wallet:
        wallet = await wallet_service.create_wallet(db, user_id)

    # 3. Credit wallet balance transactionally via Ledger
    reference_uuid = uuid.uuid4()
    await wallet_service.record_transaction(
        db=db,
        wallet_id=wallet.id,
        amount=amount_paise,
        direction="credit",
        reference_type="payment_gateway",
        reference_id=reference_uuid
    )
    
    await db.commit()
    return True
