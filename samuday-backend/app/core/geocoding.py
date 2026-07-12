"""
Free geocoding via OpenStreetMap's Nominatim, used for GPS-based address
auto-detection at checkout. No API key/billing required, unlike Google Maps —
usage must stay within Nominatim's usage policy (max ~1 request/second, and a
descriptive User-Agent is required). Swap for Google's Geocoding API later if
a Google Maps key is added — see app/core/config.py GOOGLE_MAPS_API_KEY.
"""
import logging
import httpx

logger = logging.getLogger(__name__)

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
USER_AGENT = "SamudayMarketplace/1.0 (community commerce platform)"


async def reverse_geocode(lat: float, lng: float) -> dict:
    """Converts GPS coordinates into a human-readable address breakdown."""
    url = f"{NOMINATIM_BASE_URL}/reverse"
    params = {"lat": lat, "lon": lng, "format": "jsonv2", "addressdetails": 1}
    headers = {"User-Agent": USER_AGENT}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                addr = data.get("address", {})
                return {
                    "display_name": data.get("display_name"),
                    "address_line1": " ".join(filter(None, [addr.get("house_number"), addr.get("road")])) or addr.get("suburb", ""),
                    "city": addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or "",
                    "state": addr.get("state", ""),
                    "pincode": addr.get("postcode", ""),
                    "latitude": lat,
                    "longitude": lng,
                }
    except Exception as e:
        logger.error(f"Reverse geocoding failed: {e}")
    return {}


async def forward_geocode(query: str) -> list:
    """Searches for addresses matching free-text input (manual address entry autocomplete)."""
    url = f"{NOMINATIM_BASE_URL}/search"
    params = {"q": query, "format": "jsonv2", "addressdetails": 1, "limit": 5, "countrycodes": "in"}
    headers = {"User-Agent": USER_AGENT}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                results = []
                for item in resp.json():
                    addr = item.get("address", {})
                    results.append({
                        "display_name": item.get("display_name"),
                        "address_line1": " ".join(filter(None, [addr.get("house_number"), addr.get("road")])) or addr.get("suburb", ""),
                        "city": addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or "",
                        "state": addr.get("state", ""),
                        "pincode": addr.get("postcode", ""),
                        "latitude": float(item["lat"]) if item.get("lat") else None,
                        "longitude": float(item["lon"]) if item.get("lon") else None,
                    })
                return results
    except Exception as e:
        logger.error(f"Forward geocoding failed: {e}")
    return []
