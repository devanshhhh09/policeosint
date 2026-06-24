"""
Investigations endpoint — Phase 2 + Phase 3
Wires all OSINT services
"""
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import json, structlog

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.db.models.investigation import Investigation, InvestigationStatus, InvestigationResult
from app.db.models.audit import AuditLog, AuditAction
from app.db.models.user import User
from app.schemas.investigation import InvestigationCreate, InvestigationResponse
from app.api.deps import get_current_user, require_perm

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/", response_model=InvestigationResponse, status_code=201)
async def start_investigation(
    data: InvestigationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("investigate:run")),
):
    inv = Investigation(
        case_id=data.case_id,
        investigator_id=current_user.id,
        investigation_type=data.investigation_type,
        query=data.query,
        query_type=data.query_type,
        status=InvestigationStatus.RUNNING,
    )
    db.add(inv)
    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.INVESTIGATION_RUN,
        resource="investigation",
        description=f"{data.investigation_type}: {data.query}",
        status="success",
    ))
    await db.commit()
    await db.refresh(inv)
    background_tasks.add_task(
        _run_background,
        str(inv.id), data.investigation_type,
        data.query, data.query_type or ""
    )
    return InvestigationResponse.model_validate(inv)


async def _run_background(inv_id: str, inv_type: str, query: str, query_type: str):
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Investigation).where(Investigation.id == UUID(inv_id)))
        inv = result.scalar_one_or_none()
        if not inv: return
        try:
            raw  = await _dispatch(inv_type, query, query_type)
            inv.progress        = 100.0
            inv.status          = InvestigationStatus.COMPLETED
            inv.risk_score      = float(raw.get("risk_score", 0))
            inv.summary         = raw.get("summary", "")
            inv.sources_queried = list(raw.get("sources", {}).keys())
            for src_name, src_data in raw.get("sources", {}).items():
                if isinstance(src_data, dict):
                    db.add(InvestigationResult(
                        investigation_id=inv.id,
                        source_name=src_name,
                        parsed_data=src_data,
                        raw_data=json.dumps(src_data),
                        is_suspicious=src_data.get("severity") in ("HIGH","CRITICAL"),
                    ))
            await db.commit()
            logger.info("Investigation complete", id=inv_id, risk=inv.risk_score)
        except Exception as e:
            logger.error("Investigation failed", id=inv_id, error=str(e))
            inv.status        = InvestigationStatus.FAILED
            inv.error_message = str(e)
            await db.commit()


async def _dispatch(inv_type: str, query: str, query_type: str) -> dict:
    if inv_type == "identity":
        from app.services.osint.identity import investigate_identity
        return await investigate_identity(query_type or "email", query)
    if inv_type == "ip":
        from app.services.osint.ip import investigate_ip
        return await investigate_ip(query)
    if inv_type == "domain":
        from app.services.osint.domain import investigate_domain
        return await investigate_domain(query)
    if inv_type == "upi_fraud":
        from app.services.osint.upi import investigate_upi
        return await investigate_upi(query_type or "upi_id", query)
    if inv_type == "threat":
        from app.services.osint.threat import investigate_threat
        return await investigate_threat(query_type or "ip", query)
    if inv_type == "dark_web":
        from app.services.osint.darkweb import monitor_dark_web
        return await monitor_dark_web(query_type or "email", query)
    if inv_type == "geoint":
        from app.services.osint.geoint import investigate_geoint
        return await investigate_geoint(query_type or "coordinates", query)
    if inv_type == "media":
        from app.services.osint.media import investigate_media
        return await investigate_media(query_type or "image_url", query)
    return {"risk_score": 0, "summary": f"{inv_type} — not implemented", "sources": {}}


@router.get("/{inv_id}")
async def get_investigation(
    inv_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("investigate:run")),
):
    result = await db.execute(select(Investigation).where(Investigation.id == inv_id))
    inv = result.scalar_one_or_none()
    if not inv: raise NotFoundError("Investigation", str(inv_id))
    res_rows = (await db.execute(
        select(InvestigationResult).where(InvestigationResult.investigation_id == inv_id)
    )).scalars().all()
    return {
        **InvestigationResponse.model_validate(inv).model_dump(),
        "results": [
            {"source_name": r.source_name, "parsed_data": r.parsed_data,
             "is_suspicious": r.is_suspicious}
            for r in res_rows
        ],
    }


@router.get("/")
async def list_investigations(
    case_id: UUID = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("investigate:run")),
):
    q = select(Investigation).where(Investigation.investigator_id == current_user.id)
    if case_id: q = q.where(Investigation.case_id == case_id)
    q = q.order_by(Investigation.created_at.desc())
    result = await db.execute(q.offset((page-1)*per_page).limit(per_page))
    return [InvestigationResponse.model_validate(i) for i in result.scalars().all()]


@router.delete("/{inv_id}", status_code=204)
async def delete_investigation(
    inv_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("investigate:run")),
):
    result = await db.execute(select(Investigation).where(Investigation.id == inv_id))
    inv = result.scalar_one_or_none()
    if not inv: raise NotFoundError("Investigation", str(inv_id))
    await db.delete(inv)
    await db.commit()


# Phase 4 addition — patch _dispatch to add crypto
_original_dispatch = _dispatch

async def _dispatch(inv_type: str, query: str, query_type: str) -> dict:
    if inv_type == "crypto":
        from app.services.osint.crypto import investigate_crypto
        return await investigate_crypto(query_type or "auto", query)
    return await _original_dispatch(inv_type, query, query_type)
