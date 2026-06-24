"""UPI cluster analysis endpoint — Phase 4"""
from fastapi import APIRouter, Depends
from app.db.models.user import User
from app.api.deps import get_current_user
from app.services.osint.upi_cluster import build_upi_cluster

router = APIRouter()


@router.get("/{upi_id}")
async def get_upi_cluster(
    upi_id: str,
    current_user: User = Depends(get_current_user),
):
    return build_upi_cluster(upi_id)
