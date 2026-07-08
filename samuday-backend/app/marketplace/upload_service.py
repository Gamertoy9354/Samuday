import os
import uuid
from fastapi import UploadFile
from app.core.config import settings

class UploadService:
    @staticmethod
    async def save_file(file: UploadFile) -> str:
        """
        Saves uploaded product images to local static storage.
        """
        os.makedirs("static/uploads", exist_ok=True)
        ext = os.path.splitext(file.filename or "")[1] or ".jpg"
        new_filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join("static/uploads", new_filename)
        
        file_bytes = await file.read()
        with open(filepath, "wb") as f:
            f.write(file_bytes)
            
        # Return URL relative to server root
        host_url = settings.FRONTEND_URL.replace("5173", "8000")
        return f"{host_url}/static/uploads/{new_filename}"

upload_service = UploadService()
