import asyncio
import logging
import meilisearch
from app.core.config import settings
from app.marketplace.models import Listing

logger = logging.getLogger(__name__)

# Initialize Meilisearch client
client = meilisearch.Client(settings.MEILI_URL, settings.MEILI_MASTER_KEY)

def _add_document_sync(doc: dict):
    """Synchronous function to interact with Meilisearch Client."""
    index = client.index("listings")
    index.add_documents([doc])

async def sync_listing_to_search(listing: Listing):
    """
    Syncs a listing's structured attributes to Meilisearch index.
    Runs inside a threadpool to prevent blocking the async event loop.
    """
    doc = {
        "id": str(listing.id),
        "seller_id": str(listing.seller_id),
        "pillar": listing.pillar,
        "category_id": str(listing.category_id) if listing.category_id else None,
        "title": listing.title,
        "description": listing.description,
        "price": listing.price,
        "listing_type": listing.listing_type,
        "quantity": listing.quantity,
        "unit": listing.unit,
        "status": listing.status,
        "created_at": listing.created_at.isoformat() if listing.created_at else None,
        "_geo": None
    }

    # Extract or mock geo coordinates from geohash for radius querying
    if listing.location_geohash:
        # Default mock coordinates (e.g. Ahmedabad, Gujarat center) if geohash is set
        doc["_geo"] = {"lat": 23.0225, "lng": 72.5714}

    try:
        # Offload synchronous network call to a worker thread
        await asyncio.to_thread(_add_document_sync, doc)
    except Exception as e:
        logger.error(f"Failed to sync listing {listing.id} to Meilisearch: {e}")

def _search_listings_sync(query: str, lat: float, lng: float, radius_km: float) -> list:
    """Synchronous search function utilizing Meilisearch _geoRadius filter."""
    index = client.index("listings")
    radius_meters = int(radius_km * 1000)
    # Meilisearch filters geo location using _geoRadius(latitude, longitude, distance_in_meters)
    return index.search(query, {
        "filter": f"_geoRadius({lat}, {lng}, {radius_meters})"
    })["hits"]

async def search_listings(query: str, lat: float, lng: float, radius_km: float) -> list:
    """
    Performs a radius-based geographical search.
    Runs inside a threadpool to protect event loop timing.
    """
    try:
        return await asyncio.to_thread(_search_listings_sync, query, lat, lng, radius_km)
    except Exception as e:
        logger.error(f"Meilisearch search failed: {e}")
        return []
