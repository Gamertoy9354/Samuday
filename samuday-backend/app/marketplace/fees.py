import uuid
from app.core.config import settings

# Fixed system account that accrues platform fee revenue, analogous to the
# demo catalog's SYSTEM_SELLER_ID pattern in app/seed_demo.py. Must exist as a
# real user + wallet — bootstrapped by ensure_platform_house_account().
PLATFORM_HOUSE_USER_ID = uuid.UUID("00000000-0000-4000-9000-000000000001")


def calculate_order_fees(product_amount_paise: int) -> dict:
    """
    Splits a product's price into what the buyer pays vs. what the seller/platform get.
    Delivery fee is NOT included here — it's calculated separately (needs pickup/
    destination pincodes) and added on top by the caller.

    Buyer pays: product_amount + platform_fee_amount (+ delivery fee, added by caller)
    Seller receives: product_amount (in full — the platform fee is additive, not a cut)
    Platform revenue: platform_fee_amount, minus an estimated gateway processing cost
    (gateway_fee_estimate) for bookkeeping — no real gateway is connected yet, so this
    is informational only until one is.
    """
    platform_fee_amount = round(product_amount_paise * settings.PLATFORM_FEE_RATE)
    gateway_fee_estimate = round(product_amount_paise * settings.ESTIMATED_GATEWAY_FEE_RATE)
    return {
        "product_amount": product_amount_paise,
        "platform_fee_amount": platform_fee_amount,
        "gateway_fee_estimate": gateway_fee_estimate,
        "net_platform_revenue_estimate": platform_fee_amount - gateway_fee_estimate,
    }
