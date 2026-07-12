"""
Delhivery API client.

Endpoint shapes and parameter names below are built from Delhivery's public
"Last-Mile API Integration" docs (delhivery-express-api-doc.readme.io). Delhivery
gates the exact production URLs and full request/response schemas behind a login
to their Developer Portal (one.delhivery.com/developer-portal) — verify these
against that portal once real API credentials exist, before going live.

Every public function here checks settings.DELHIVERY_API_KEY. When it's unset
(the default — no Delhivery account exists yet), functions return clearly-labeled
simulated results instead of failing, so the rest of the checkout/shipping flow
can be built and tested end-to-end today.
"""
import logging
from typing import Optional
from uuid import UUID
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

DELHIVERY_BASE_URL = "https://track.delhivery.com"


def is_delhivery_connected() -> bool:
    return bool(settings.DELHIVERY_API_KEY)


def _simulated_rate_paise(weight_grams: int, origin_pincode: str, destination_pincode: str) -> int:
    """
    Rough distance-agnostic estimate used only when no real Delhivery account is
    connected: a base fee plus a per-500g increment. Real rates depend on zone
    (same city/state/metro/rest-of-India) which requires Delhivery's live API.
    """
    base_paise = 4000  # Rs 40 base
    weight_increment = max(0, (weight_grams - 500)) // 500
    increment_paise = weight_increment * 1500  # Rs 15 per extra 500g
    # Small deterministic variation by pincode pair so it doesn't look hardcoded
    zone_bump = 1000 if origin_pincode[:2] != destination_pincode[:2] else 0
    return base_paise + increment_paise + zone_bump


async def calculate_shipping_rate(
    weight_grams: int,
    origin_pincode: str,
    destination_pincode: str,
    mode: str = "E",  # E = Express, S = Surface
) -> dict:
    """
    Returns {"amount_paise": int, "is_simulated": bool}.
    Real endpoint (per Delhivery docs): GET /api/kinko/v1/invoice/charges/.json
    Params: md (billing mode E/S), cgm (chargeable weight in grams), o_pin, d_pin,
    ss (shipment status — use "Delivered" for a forward-shipment cost estimate).
    """
    if not is_delhivery_connected():
        amount = _simulated_rate_paise(weight_grams, origin_pincode, destination_pincode)
        return {"amount_paise": amount, "is_simulated": True}

    url = f"{DELHIVERY_BASE_URL}/api/kinko/v1/invoice/charges/.json"
    headers = {"Authorization": f"Token {settings.DELHIVERY_API_KEY}"}
    params = {
        "md": mode,
        "cgm": weight_grams,
        "o_pin": origin_pincode,
        "d_pin": destination_pincode,
        "ss": "Delivered",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                # Response is documented to include total_amount (gross + tax), in rupees
                total_amount_rupees = data[0]["total_amount"] if isinstance(data, list) else data.get("total_amount")
                return {"amount_paise": round(float(total_amount_rupees) * 100), "is_simulated": False}
            logger.warning(f"Delhivery rate calc failed ({resp.status_code}): {resp.text[:300]}")
    except Exception as e:
        logger.error(f"Delhivery rate calc error: {e}")

    # Real API reachable-but-failing: fall back to the simulated estimate rather
    # than blocking checkout entirely.
    amount = _simulated_rate_paise(weight_grams, origin_pincode, destination_pincode)
    return {"amount_paise": amount, "is_simulated": True}


async def create_shipment(
    order_id: UUID,
    pickup: dict,      # {name, address, city, state, pincode, phone} — from SellerDispatchProfile
    consignee: dict,   # {name, address, city, state, pincode, phone} — from buyer's Address
    weight_grams: int,
    total_amount_paise: int,
) -> dict:
    """
    Returns {"waybill_number": Optional[str], "tracking_url": Optional[str], "is_simulated": bool}.
    Real endpoint: POST /api/cmu/create.json (Delhivery calls this "manifestation").
    Requires pickup_location.name to exactly match a warehouse name already
    registered with Delhivery for this account — cannot be created ad hoc via API.
    """
    if not is_delhivery_connected():
        logger.info(f"[Delhivery SIMULATED] Would manifest shipment for order {order_id}")
        return {"waybill_number": None, "tracking_url": None, "is_simulated": True}

    url = f"{DELHIVERY_BASE_URL}/api/cmu/create.json"
    headers = {"Authorization": f"Token {settings.DELHIVERY_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "pickup_location": {
            "name": pickup["name"],
            "add": pickup["address"],
            "city": pickup["city"],
            "state": pickup["state"],
            "pin": pickup["pincode"],
            "phone": pickup["phone"],
            "country": "India",
        },
        "shipments": [{
            "order": str(order_id),
            "name": consignee["name"],
            "add": consignee["address"],
            "city": consignee["city"],
            "state": consignee["state"],
            "pin": consignee["pincode"],
            "phone": consignee["phone"],
            "country": "India",
            "payment_mode": "Prepaid",  # buyer already paid Samuday, not COD
            "total_amount": total_amount_paise / 100,
            "weight": weight_grams,
        }],
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=20.0)
            if resp.status_code == 200:
                data = resp.json()
                packages = data.get("packages", [])
                if packages and packages[0].get("waybill"):
                    waybill = packages[0]["waybill"]
                    return {
                        "waybill_number": waybill,
                        "tracking_url": f"{DELHIVERY_BASE_URL}/track/package/{waybill}",
                        "is_simulated": False,
                    }
            logger.warning(f"Delhivery shipment creation failed ({resp.status_code}): {resp.text[:300]}")
    except Exception as e:
        logger.error(f"Delhivery shipment creation error: {e}")

    return {"waybill_number": None, "tracking_url": None, "is_simulated": True}


async def get_tracking_status(waybill_number: str) -> Optional[dict]:
    """
    Returns {"status": str, "updated_at": Optional[str]} or None if unavailable.
    Real endpoint: GET /api/v1/packages/json/?waybill={waybill_number}
    """
    if not is_delhivery_connected() or not waybill_number:
        return None

    url = f"{DELHIVERY_BASE_URL}/api/v1/packages/json/"
    headers = {"Authorization": f"Token {settings.DELHIVERY_API_KEY}"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params={"waybill": waybill_number}, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                shipment_data = data.get("ShipmentData", [])
                if shipment_data:
                    status = shipment_data[0].get("Shipment", {}).get("Status", {})
                    return {"status": status.get("Status"), "updated_at": status.get("StatusDateTime")}
    except Exception as e:
        logger.error(f"Delhivery tracking fetch error: {e}")
    return None
