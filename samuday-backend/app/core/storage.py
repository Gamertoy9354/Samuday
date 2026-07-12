import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

STORAGE_BUCKET = "listing-media"


async def upload_bytes(file_bytes: bytes, filename: str, content_type: str) -> str:
    """
    Uploads raw bytes to the Supabase Storage 'listing-media' bucket (public read,
    created via migration) using the service-role key, returning the object's
    public URL. Used instead of local disk because Render's free/ephemeral web
    service instances lose all local files on every restart or redeploy.
    """
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{filename}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, content=file_bytes, timeout=30.0)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Supabase Storage upload failed ({resp.status_code}): {resp.text[:300]}")

    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{filename}"
