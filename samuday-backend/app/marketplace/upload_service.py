import mimetypes
import os
import uuid
from fastapi import UploadFile, HTTPException, status
from app.core.storage import upload_bytes

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

class UploadService:
    @staticmethod
    async def save_file(file: UploadFile) -> str:
        """
        Uploads product images to Supabase Storage (not local disk — Render's
        free/ephemeral instances lose local files on restart). Only allows a known
        set of safe image extensions and enforces a size cap.
        """
        ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
            )

        file_bytes = await file.read()
        if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB."
            )

        new_filename = f"{uuid.uuid4().hex}{ext}"
        content_type = mimetypes.guess_type(new_filename)[0] or "application/octet-stream"

        try:
            return await upload_bytes(file_bytes, new_filename, content_type)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Image storage upload failed: {e}"
            )

upload_service = UploadService()
