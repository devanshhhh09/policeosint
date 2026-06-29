"""
Media Forensics Upload Endpoint
Accepts image upload, returns full forensics analysis
"""
import io
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from app.db.models.user import User
from app.api.deps import get_current_user, require_perm
from app.services.osint.media import investigate_media

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg","image/jpg","image/png","image/gif",
    "image/webp","image/bmp","image/tiff",
}
MAX_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_perm("investigate:run")),
):
    if file.content_type not in ALLOWED_TYPES:
        return JSONResponse(status_code=400, content={
            "error": f"Unsupported file type: {file.content_type}. Supported: JPEG, PNG, GIF, WEBP, BMP"
        })

    image_bytes = await file.read()

    if len(image_bytes) > MAX_SIZE:
        return JSONResponse(status_code=413, content={
            "error": "File too large. Maximum size is 20MB."
        })

    if len(image_bytes) < 100:
        return JSONResponse(status_code=400, content={
            "error": "File too small or empty."
        })

    result = await investigate_media(image_bytes, file.filename or "unknown")
    return result
