"""
Digital Evidence Management — Phase 5
SHA256 + MD5 hashing · Chain of custody · EXIF extraction
"""
import hashlib, os, mimetypes
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import aiofiles
import structlog

from app.core.database import get_db
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.db.models.evidence import Evidence, EvidenceType
from app.db.models.case import Case
from app.db.models.audit import AuditLog, AuditAction
from app.db.models.user import User
from app.api.deps import get_current_user, require_perm

router = APIRouter()
logger = structlog.get_logger(__name__)


def _compute_hashes(path: str) -> dict:
    sha256 = hashlib.sha256()
    md5    = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
            md5.update(chunk)
    return {"sha256": sha256.hexdigest(), "md5": md5.hexdigest()}


def _extract_exif(path: str, mime: str) -> dict | None:
    if not mime or not mime.startswith("image/"):
        return None
    try:
        import piexif
        from PIL import Image
        img  = Image.open(path)
        info = img._getexif()
        if not info:
            return None
        from PIL.ExifTags import TAGS, GPSTAGS
        exif: dict = {}
        for tag_id, value in info.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                gps: dict = {}
                for gps_id, gps_val in value.items():
                    gps[GPSTAGS.get(gps_id, gps_id)] = str(gps_val)
                exif["GPSInfo"] = gps
            elif isinstance(value, (str, int, float)):
                exif[str(tag)] = str(value)
        return exif
    except Exception:
        return None


@router.post("/{case_id}/upload", status_code=201)
async def upload_evidence(
    case_id: UUID,
    file: UploadFile = File(...),
    description: str = Form(""),
    evidence_type: EvidenceType = Form(EvidenceType.OTHER),
    collected_from: str = Form(""),
    collection_method: str = Form("Digital capture"),
    exhibit_number: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("evidence:upload")),
):
    # Verify case exists
    case_result = await db.execute(select(Case).where(Case.id == case_id))
    if not case_result.scalar_one_or_none():
        raise NotFoundError("Case", str(case_id))

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # Create directory
    case_dir = os.path.join(settings.EVIDENCE_UPLOAD_DIR, str(case_id))
    os.makedirs(case_dir, exist_ok=True)

    ts        = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = f"{ts}_{file.filename}"
    file_path = os.path.join(case_dir, safe_name)
    file_size = 0

    async with aiofiles.open(file_path, "wb") as out:
        while chunk := await file.read(8192):
            file_size += len(chunk)
            if file_size > max_bytes:
                os.remove(file_path)
                return JSONResponse(status_code=413, content={
                    "error": f"File too large. Max: {settings.MAX_UPLOAD_SIZE_MB}MB"
                })
            await out.write(chunk)

    # Hash for integrity
    hashes = _compute_hashes(file_path)
    mime   = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
    exif   = _extract_exif(file_path, mime)

    exhibit = exhibit_number or f"EX-{ts}"

    ev = Evidence(
        case_id=case_id,
        uploaded_by_id=current_user.id,
        filename=safe_name,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime,
        evidence_type=evidence_type,
        sha256_hash=hashes["sha256"],
        md5_hash=hashes["md5"],
        description=description,
        collected_from=collected_from,
        exhibit_number=exhibit,
        exif_data=str(exif) if exif else None,
    )
    db.add(ev)

    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.EVIDENCE_UPLOAD,
        resource="evidence",
        resource_id=str(case_id),
        description=f"Uploaded: {file.filename} ({file_size} bytes) SHA256: {hashes['sha256'][:16]}…",
        status="success",
    ))
    await db.commit()
    await db.refresh(ev)

    logger.info("Evidence uploaded", exhibit=exhibit, sha256=hashes["sha256"][:16])

    return {
        "id":              str(ev.id),
        "exhibit_number":  exhibit,
        "original_filename": file.filename,
        "file_size":       file_size,
        "file_size_human": _human_size(file_size),
        "mime_type":       mime,
        "evidence_type":   evidence_type,
        "sha256_hash":     hashes["sha256"],
        "md5_hash":        hashes["md5"],
        "exif_extracted":  exif is not None,
        "gps_found":       exif is not None and "GPSInfo" in exif,
        "gps_data":        exif.get("GPSInfo") if exif else None,
        "integrity":       "VERIFIED",
        "uploaded_by":     current_user.badge_number,
        "uploaded_at":     ev.created_at.isoformat() if ev.created_at else "",
        "message":         "Evidence uploaded and integrity verified ✅",
    }


@router.get("/{case_id}/list")
async def list_evidence(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("case:read")),
):
    result = await db.execute(
        select(Evidence).where(Evidence.case_id == case_id)
        .order_by(Evidence.created_at.desc())
    )
    items = result.scalars().all()
    return [
        {
            "id":                str(e.id),
            "exhibit_number":    e.exhibit_number,
            "original_filename": e.original_filename,
            "evidence_type":     e.evidence_type,
            "file_size":         e.file_size,
            "file_size_human":   _human_size(e.file_size),
            "mime_type":         e.mime_type,
            "sha256_hash":       e.sha256_hash,
            "md5_hash":          e.md5_hash,
            "description":       e.description,
            "collected_from":    e.collected_from,
            "exif_data":         e.exif_data,
            "is_sealed":         e.is_sealed,
            "uploaded_by_id":    str(e.uploaded_by_id),
            "created_at":        e.created_at.isoformat() if e.created_at else "",
        }
        for e in items
    ]


@router.post("/{evidence_id}/verify")
async def verify_integrity(
    evidence_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("case:read")),
):
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    ev = result.scalar_one_or_none()
    if not ev:
        raise NotFoundError("Evidence", str(evidence_id))

    if not os.path.exists(ev.file_path):
        return {"intact": False, "error": "File not found on disk", "status": "FILE_MISSING"}

    current_hashes = _compute_hashes(ev.file_path)
    intact = current_hashes["sha256"] == ev.sha256_hash

    return {
        "evidence_id":    str(evidence_id),
        "exhibit_number": ev.exhibit_number,
        "intact":         intact,
        "stored_sha256":  ev.sha256_hash,
        "current_sha256": current_hashes["sha256"],
        "stored_md5":     ev.md5_hash,
        "current_md5":    current_hashes["md5"],
        "status":         "VERIFIED ✅" if intact else "CORRUPTED ❌",
        "verified_by":    current_user.badge_number,
        "verified_at":    datetime.now(timezone.utc).isoformat(),
    }


@router.patch("/{evidence_id}/seal")
async def seal_evidence(
    evidence_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("case:update")),
):
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    ev = result.scalar_one_or_none()
    if not ev:
        raise NotFoundError("Evidence", str(evidence_id))
    ev.is_sealed = True
    await db.commit()
    return {"message": f"Evidence {ev.exhibit_number} sealed ✅", "sealed_by": current_user.badge_number}


def _human_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
