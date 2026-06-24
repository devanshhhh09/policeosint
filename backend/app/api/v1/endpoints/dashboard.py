"""
Dashboard endpoint — Phase 5 + Net Scrapper integration
Shows active cases + live internet scam intelligence combined
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta, timezone
from app.core.database import get_db
from app.db.models.case import Case, CaseStatus, CasePriority, CaseType
from app.db.models.investigation import Investigation, InvestigationType, InvestigationStatus
from app.db.models.evidence import Evidence
from app.db.models.audit import AuditLog
from app.db.models.user import User
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now       = datetime.now(timezone.utc)
    week_ago  = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    day_ago   = now - timedelta(days=1)

    # ── Case stats ─────────────────────────────────────────────
    total_cases    = (await db.execute(select(func.count(Case.id)))).scalar() or 0
    active_cases   = (await db.execute(select(func.count(Case.id)).where(Case.status == CaseStatus.ACTIVE))).scalar() or 0
    closed_cases   = (await db.execute(select(func.count(Case.id)).where(Case.status == CaseStatus.CLOSED))).scalar() or 0
    critical_cases = (await db.execute(select(func.count(Case.id)).where(Case.priority == CasePriority.CRITICAL))).scalar() or 0
    new_week       = (await db.execute(select(func.count(Case.id)).where(Case.created_at >= week_ago))).scalar() or 0
    new_today      = (await db.execute(select(func.count(Case.id)).where(Case.created_at >= day_ago))).scalar() or 0

    type_counts = {}
    for ct in CaseType:
        cnt = (await db.execute(select(func.count(Case.id)).where(Case.case_type == ct))).scalar() or 0
        if cnt > 0:
            type_counts[ct.value] = cnt

    # ── Investigation stats ────────────────────────────────────
    inv_total = (await db.execute(select(func.count(Investigation.id)))).scalar() or 0
    inv_month = (await db.execute(select(func.count(Investigation.id)).where(Investigation.created_at >= month_ago))).scalar() or 0
    inv_today = (await db.execute(select(func.count(Investigation.id)).where(Investigation.created_at >= day_ago))).scalar() or 0
    inv_running=(await db.execute(select(func.count(Investigation.id)).where(Investigation.status == InvestigationStatus.RUNNING))).scalar() or 0

    inv_types = {}
    for it in InvestigationType:
        cnt = (await db.execute(select(func.count(Investigation.id)).where(Investigation.investigation_type == it))).scalar() or 0
        if cnt > 0:
            inv_types[it.value] = cnt

    # ── Evidence stats ─────────────────────────────────────────
    evidence_total = (await db.execute(select(func.count(Evidence.id)))).scalar() or 0
    evidence_week  = (await db.execute(select(func.count(Evidence.id)).where(Evidence.created_at >= week_ago))).scalar() or 0

    # ── Net Scrapper stats (internet scams) ────────────────────
    net_stats = await _get_net_scrapper_stats(db)

    # ── Financial stats ────────────────────────────────────────
    amount_result = await db.execute(select(Case.amount_lost).where(Case.amount_lost.isnot(None)))
    amounts    = [int(r or 0) for r in amount_result.scalars().all()]
    total_lost = sum(amounts)

    # ── Recent cases (by time) ─────────────────────────────────
    recent_result = await db.execute(
        select(Case).order_by(Case.created_at.desc()).limit(10)
    )
    recent_cases = recent_result.scalars().all()

    # ── Active investigations by case ──────────────────────────
    active_inv_result = await db.execute(
        select(Investigation)
        .where(Investigation.status.in_([InvestigationStatus.RUNNING, InvestigationStatus.PENDING]))
        .order_by(Investigation.created_at.desc()).limit(10)
    )
    active_invs = active_inv_result.scalars().all()

    return {
        "cases": {
            "total":         total_cases,
            "active":        active_cases,
            "closed":        closed_cases,
            "critical":      critical_cases,
            "new_today":     new_today,
            "new_this_week": new_week,
            "by_type":       type_counts,
        },
        "investigations": {
            "total":        inv_total,
            "last_30_days": inv_month,
            "today":        inv_today,
            "running":      inv_running,
            "by_type":      inv_types,
        },
        "evidence": {
            "total_items":     evidence_total,
            "added_this_week": evidence_week,
        },
        "financial": {
            "total_loss_inr":    total_lost,
            "total_loss_lakh":   round(total_lost / 100000, 2),
            "cases_with_amount": len(amounts),
        },
        "internet_scams": net_stats,
        "user": {
            "role":    current_user.role,
            "station": current_user.station_name,
            "name":    current_user.full_name,
        },
        "recent_cases": [
            {
                "id":          str(c.id),
                "case_number": c.case_number,
                "title":       c.title,
                "case_type":   c.case_type,
                "status":      c.status,
                "priority":    c.priority,
                "amount_lost": c.amount_lost,
                "victim_name": c.victim_name,
                "created_at":  c.created_at.isoformat() if c.created_at else "",
            }
            for c in recent_cases
        ],
        "active_investigations": [
            {
                "id":               str(inv.id),
                "investigation_type": str(inv.investigation_type).replace("InvestigationType.",""),
                "query":            inv.query,
                "status":           str(inv.status).replace("InvestigationStatus.",""),
                "risk_score":       inv.risk_score or 0,
                "case_id":          str(inv.case_id) if inv.case_id else None,
                "created_at":       inv.created_at.isoformat() if inv.created_at else "",
            }
            for inv in active_invs
        ],
    }


async def _get_net_scrapper_stats(db: AsyncSession) -> dict:
    """Get internet scam scraper stats."""
    try:
        from app.modules.net_scrapper.models import (
            ScrapedSource, ExtractedContent, ExtractedIndicator,
            SourceStatus, ContentCategory
        )
        total_sources  = (await db.execute(select(func.count(ScrapedSource.id)))).scalar() or 0
        active_sources = (await db.execute(select(func.count(ScrapedSource.id)).where(ScrapedSource.status == SourceStatus.ACTIVE))).scalar() or 0
        total_content  = (await db.execute(select(func.count(ExtractedContent.id)))).scalar() or 0
        flagged        = (await db.execute(select(func.count(ExtractedContent.id)).where(ExtractedContent.is_flagged == True))).scalar() or 0
        critical       = (await db.execute(select(func.count(ExtractedContent.id)).where(ExtractedContent.risk_score >= 80))).scalar() or 0
        total_inds     = (await db.execute(select(func.count(ExtractedIndicator.id)))).scalar() or 0
        high_risk_inds = (await db.execute(select(func.count(ExtractedIndicator.id)).where(ExtractedIndicator.risk_score >= 70))).scalar() or 0

        by_category = {}
        for c in ContentCategory:
            cnt = (await db.execute(select(func.count(ExtractedContent.id)).where(ExtractedContent.category == c))).scalar() or 0
            if cnt > 0:
                by_category[c.value] = cnt

        return {
            "total_sources":       total_sources,
            "active_sources":      active_sources,
            "total_scams_found":   total_content,
            "flagged":             flagged,
            "critical":            critical,
            "total_iocs":          total_inds,
            "high_risk_iocs":      high_risk_inds,
            "by_category":         by_category,
            "available":           True,
        }
    except Exception:
        return {"available": False, "total_scams_found": 0, "flagged": 0, "critical": 0}


@router.get("/alerts")
async def live_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now     = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)

    alerts = []

    # Critical cases
    crit_result = await db.execute(
        select(Case).where(
            and_(Case.priority == CasePriority.CRITICAL, Case.status == CaseStatus.ACTIVE)
        ).order_by(Case.created_at.desc()).limit(3)
    )
    for c in crit_result.scalars().all():
        alerts.append({
            "id":          str(c.id),
            "type":        "critical_case",
            "title":       f"CRITICAL: {c.title[:50]}",
            "description": f"{c.case_number} · {str(c.case_type).replace('CaseType.','').replace('_',' ').title()}",
            "severity":    "critical",
            "category":    "case",
            "url":         f"/cases/{c.id}",
            "is_read":     False,
            "created_at":  c.created_at.isoformat() if c.created_at else "",
        })

    # High risk investigations
    inv_result = await db.execute(
        select(Investigation).where(
            and_(Investigation.risk_score >= 70, Investigation.created_at >= day_ago)
        ).order_by(Investigation.risk_score.desc()).limit(3)
    )
    for inv in inv_result.scalars().all():
        inv_type = str(inv.investigation_type).replace("InvestigationType.","").replace("_"," ").title()
        alerts.append({
            "id":          str(inv.id),
            "type":        "high_risk_investigation",
            "title":       f"High risk {inv_type} investigation",
            "description": f"Target: {inv.query[:40]} · Risk: {inv.risk_score:.0f}/100",
            "severity":    "high",
            "category":    str(inv.investigation_type).replace("InvestigationType.",""),
            "url":         f"/investigations/{inv.id}",
            "is_read":     False,
            "created_at":  inv.created_at.isoformat() if inv.created_at else "",
        })

    # Internet scam alerts
    try:
        from app.modules.net_scrapper.models import ExtractedContent, ContentCategory
        scam_result = await db.execute(
            select(ExtractedContent).where(
                and_(ExtractedContent.is_flagged == True, ExtractedContent.risk_score >= 70)
            ).order_by(ExtractedContent.risk_score.desc()).limit(3)
        )
        for scam in scam_result.scalars().all():
            alerts.append({
                "id":          str(scam.id),
                "type":        "internet_scam",
                "title":       f"Internet scam detected: {str(scam.category).replace('ContentCategory.','').replace('_',' ').title()}",
                "description": (scam.content_text or "")[:80],
                "severity":    "critical" if scam.risk_score >= 80 else "high",
                "category":    "internet_scam",
                "url":         "/net-scrapper/telegram",
                "is_read":     False,
                "created_at":  scam.scraped_at.isoformat() if scam.scraped_at else "",
            })
    except Exception:
        pass

    # Static threat intel alerts
    alerts += [
        {
            "id": "ti_001", "type": "threat_intel",
            "title": "APT SideCopy — Indian Govt targeting campaign",
            "description": "MITRE T1566.001 · Spear-phishing · 14 IOCs · Source: OTX",
            "severity": "critical", "category": "apt",
            "url": "/threat", "is_read": False,
            "created_at": (now - timedelta(hours=2)).isoformat(),
        },
        {
            "id": "ti_002", "type": "dark_web",
            "title": "Credential dump — .gov.in emails on BreachForums",
            "description": "1,200 government email accounts exposed",
            "severity": "high", "category": "dark_web",
            "url": "/darkweb", "is_read": False,
            "created_at": (now - timedelta(hours=5)).isoformat(),
        },
    ]

    alerts.sort(key=lambda x: (x["severity"] == "critical", x["created_at"]), reverse=True)

    return {
        "alerts":       alerts[:12],
        "total":        len(alerts),
        "unread_count": sum(1 for a in alerts if not a["is_read"]),
    }


@router.get("/timeline")
async def activity_timeline(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    case_result = await db.execute(
        select(Case).where(Case.created_at >= week_ago)
        .order_by(Case.created_at.desc()).limit(8)
    )
    inv_result = await db.execute(
        select(Investigation).where(Investigation.created_at >= week_ago)
        .order_by(Investigation.created_at.desc()).limit(8)
    )
    cases = case_result.scalars().all()
    invs  = inv_result.scalars().all()

    events = []
    for c in cases:
        events.append({
            "type":        "case_created",
            "title":       f"Case: {c.case_number}",
            "description": c.title[:60],
            "icon":        "ti-folder-plus",
            "color":       "red" if c.priority == CasePriority.CRITICAL else "blue",
            "priority":    str(c.priority).replace("CasePriority.",""),
            "url":         f"/cases/{c.id}",
            "timestamp":   c.created_at.isoformat() if c.created_at else "",
        })
    for inv in invs:
        inv_type = str(inv.investigation_type).replace("InvestigationType.","").replace("_"," ").title()
        risk     = inv.risk_score or 0
        events.append({
            "type":        "investigation",
            "title":       f"{inv_type} investigation",
            "description": f"Target: {inv.query[:40]} · Risk: {risk:.0f}/100",
            "icon":        "ti-search",
            "color":       "red" if risk > 70 else "purple" if risk > 40 else "green",
            "risk_score":  risk,
            "url":         f"/investigate/{str(inv.investigation_type).replace('InvestigationType.','').lower()}",
            "timestamp":   inv.created_at.isoformat() if inv.created_at else "",
        })

    # Internet scam events
    try:
        from app.modules.net_scrapper.models import ExtractedContent
        scam_result = await db.execute(
            select(ExtractedContent)
            .where(and_(ExtractedContent.is_flagged == True, ExtractedContent.scraped_at >= week_ago))
            .order_by(ExtractedContent.scraped_at.desc()).limit(5)
        )
        for scam in scam_result.scalars().all():
            events.append({
                "type":        "internet_scam",
                "title":       f"Internet scam: {str(scam.category).replace('ContentCategory.','').replace('_',' ').title()}",
                "description": (scam.content_text or "")[:60],
                "icon":        "ti-world-search",
                "color":       "red",
                "risk_score":  scam.risk_score,
                "url":         "/net-scrapper/telegram",
                "timestamp":   scam.scraped_at.isoformat() if scam.scraped_at else "",
            })
    except Exception:
        pass

    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"events": events[:20]}


@router.get("/cases-by-time")
async def cases_by_time(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cases timeline grouped by day for the last 30 days."""
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    result    = await db.execute(
        select(Case).where(Case.created_at >= month_ago)
        .order_by(Case.created_at.desc())
    )
    cases = result.scalars().all()

    # Group by day
    by_day: dict[str, dict] = {}
    for c in cases:
        day = c.created_at.strftime("%Y-%m-%d") if c.created_at else "unknown"
        if day not in by_day:
            by_day[day] = {"date": day, "total": 0, "critical": 0, "active": 0, "closed": 0, "cases": []}
        by_day[day]["total"] += 1
        if str(c.priority) in ("critical", "CasePriority.critical"):
            by_day[day]["critical"] += 1
        if str(c.status) in ("active", "CaseStatus.active"):
            by_day[day]["active"] += 1
        if str(c.status) in ("closed", "CaseStatus.closed"):
            by_day[day]["closed"] += 1
        by_day[day]["cases"].append({
            "id":          str(c.id),
            "case_number": c.case_number,
            "title":       c.title[:60],
            "case_type":   str(c.case_type).replace("CaseType.",""),
            "status":      str(c.status).replace("CaseStatus.",""),
            "priority":    str(c.priority).replace("CasePriority.",""),
            "amount_lost": c.amount_lost,
        })

    return {
        "days":      sorted(by_day.values(), key=lambda x: x["date"], reverse=True),
        "total":     len(cases),
        "span_days": 30,
    }


@router.get("/active-investigations")
async def active_investigations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All running/pending investigations with case context."""
    result = await db.execute(
        select(Investigation)
        .order_by(Investigation.created_at.desc())
        .limit(50)
    )
    invs = result.scalars().all()

    return [
        {
            "id":                str(inv.id),
            "investigation_type":str(inv.investigation_type).replace("InvestigationType.",""),
            "query":             inv.query,
            "status":            str(inv.status).replace("InvestigationStatus.",""),
            "risk_score":        inv.risk_score or 0,
            "summary":           inv.summary or "",
            "case_id":           str(inv.case_id) if inv.case_id else None,
            "sources_queried":   inv.sources_queried or [],
            "created_at":        inv.created_at.isoformat() if inv.created_at else "",
            "updated_at":        inv.updated_at.isoformat() if inv.updated_at else "",
        }
        for inv in invs
    ]
