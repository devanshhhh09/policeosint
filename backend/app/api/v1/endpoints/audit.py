from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from app.core.database import get_db
from app.db.models.audit import AuditLog
from app.db.models.user import User
from app.api.deps import require_perm

router = APIRouter()

@router.get("/")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, le=200),
    action: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("audit:view")),
):
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action: q = q.where(AuditLog.action == action)
    total  = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    result = await db.execute(q.offset((page - 1) * per_page).limit(per_page))
    logs   = result.scalars().all()
    return {
        "logs": [
            {
                "id":          str(l.id),
                "user_id":     str(l.user_id) if l.user_id else None,
                "action":      l.action,
                "resource":    l.resource,
                "resource_id": l.resource_id,
                "description": l.description,
                "ip_address":  l.ip_address,
                "status":      l.status,
                "created_at":  l.created_at,
            }
            for l in logs
        ],
        "total": total, "page": page, "per_page": per_page,
    }
