import hmac
import hashlib
import os
import uuid
import logging
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.wallet import service as wallet_service
from app.wallet.models import PaymentOrder

logger = logging.getLogger(__name__)


def _sign(gateway_order_id: str, user_id: UUID, amount_paise: int) -> str:
    """Computes an HMAC-SHA256 signature binding an order to its owner and fixed amount."""
    message = f"{gateway_order_id}:{user_id}:{amount_paise}".encode("utf-8")
    return hmac.new(settings.PAYMENT_WEBHOOK_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()


async def create_payment_checkout(db: AsyncSession, amount_paise: int, current_user_id: UUID) -> dict:
    """
    Creates a payment checkout order, persisting the fixed amount server-side so it
    cannot be tampered with by the client during the callback step.
    Stubs Razorpay / Cashfree order creation formats.
    """
    gateway_order_id = f"order_pay_{uuid.uuid4().hex[:12]}"
    gateway_provider = os.getenv("PAYMENT_PROVIDER", "razorpay")
    checkout_url = f"https://checkout.{gateway_provider}.com/pay/{gateway_order_id}"

    order = PaymentOrder(
        gateway_order_id=gateway_order_id,
        user_id=current_user_id,
        amount=amount_paise,
        status="created"
    )
    db.add(order)
    await db.commit()

    logger.info(f"[Payment Gateway] Created {gateway_provider} order {gateway_order_id} for user {current_user_id} of amount {amount_paise} paise")

    return {
        "gateway_order_id": gateway_order_id,
        "amount": amount_paise,
        "currency": "INR",
        "checkout_url": checkout_url,
        "status": "created",
        # In a real integration this signature is produced by the gateway itself and returned
        # to the client after a successful charge. We pre-compute it here since this is a
        # sandbox/mock gateway with no real payment processor behind it.
        "signature": _sign(gateway_order_id, current_user_id, amount_paise)
    }


async def callback_payment_verification(
    db: AsyncSession,
    gateway_order_id: str,
    payment_id: str,
    signature: str,
    user_id: UUID,
) -> Optional[int]:
    """
    Handles payment gateway success callback verification.
    Looks up the order created at checkout time (never trusts a client-supplied amount),
    verifies the HMAC signature, and enforces the order can only be completed once.
    If valid, automatically credits the user's wallet balance using the double-entry ledger.
    Returns the credited amount in paise, or None if verification failed.
    """
    result = await db.execute(
        select(PaymentOrder).where(PaymentOrder.gateway_order_id == gateway_order_id).with_for_update()
    )
    order = result.scalars().first()
    if not order:
        logger.warning(f"[Payment Callback] Unknown order {gateway_order_id}")
        return None

    if order.user_id != user_id:
        logger.warning(f"[Payment Callback] Order {gateway_order_id} does not belong to user {user_id}")
        return None

    if order.status == "completed":
        logger.warning(f"[Payment Callback] Order {gateway_order_id} already completed; ignoring replay")
        return None

    expected_signature = _sign(gateway_order_id, user_id, order.amount)
    if not signature or not hmac.compare_digest(signature, expected_signature):
        logger.warning(f"[Payment Callback] Signature mismatch for order {gateway_order_id}")
        return None

    logger.info(f"[Payment Callback] Verified signature for order {gateway_order_id}, payment_id: {payment_id}")

    # Get or create wallet
    wallet = await wallet_service.get_wallet_by_user_id(db, user_id)
    if not wallet:
        wallet = await wallet_service.create_wallet(db, user_id)

    # Credit wallet balance transactionally via Ledger, using the amount fixed at checkout time
    reference_uuid = uuid.uuid4()
    await wallet_service.record_transaction(
        db=db,
        wallet_id=wallet.id,
        amount=order.amount,
        direction="credit",
        reference_type="payment_gateway",
        reference_id=reference_uuid
    )

    from datetime import datetime, timezone
    order.status = "completed"
    order.completed_at = datetime.now(timezone.utc)

    await db.commit()
    return order.amount
