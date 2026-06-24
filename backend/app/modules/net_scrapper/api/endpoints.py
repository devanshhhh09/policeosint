"""
Net Scrapper & Intelligence Hub — API Endpoints
Prefix: /api/v1/scrapper
"""
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from uuid import UUID
from datetime import datetime, timezone
import asyncio

from app.core.database import get_db
from app.db.models.user import User
from app.api.deps import get_current_user, require_perm
from app.modules.net_scrapper.models import (
    ScrapedSource, ExtractedContent, ExtractedIndicator,
    SourceCreate, SourceResponse, ContentResponse, IndicatorResponse,
    SourcePlatform, SourceStatus, ContentCategory, IndicatorType, ScraperStats
)
from app.modules.net_scrapper.services.content_analyzer import analyze_content
from app.modules.net_scrapper.services.telegram_monitor import (
    get_channel_info, scrape_recent_messages, start_monitor, stop_monitor, get_active_monitors
)
from app.modules.net_scrapper.services.osint_orchestrator import (
    run_sherlock, run_maigret, run_holehe, run_theharvester
)

router = APIRouter()


# ── Sources ───────────────────────────────────────────────────────────────────
@router.post("/sources", response_model=SourceResponse, status_code=201)
async def add_source(
    data: SourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("investigate:run")),
):
    """Add a new Telegram channel, Twitter account, or Instagram profile to monitor."""
    # Get channel info if Telegram
    display_name = data.display_name
    meta         = {}

    if data.platform == SourcePlatform.TELEGRAM:
        info         = await get_channel_info(data.identifier)
        display_name = display_name or info.get("title", data.identifier)
        meta         = info

    source = ScrapedSource(
        platform=data.platform,
        identifier=data.identifier,
        display_name=display_name or data.identifier,
        description=data.description,
        status=SourceStatus.ACTIVE,
        added_by=current_user.id,
        meta=meta,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return SourceResponse(
        id=str(source.id), platform=source.platform,
        identifier=source.identifier, display_name=source.display_name,
        status=source.status, is_auto=source.is_auto,
        message_count=source.message_count, last_scraped=source.last_scraped,
        created_at=source.created_at,
    )


@router.get("/sources")
async def list_sources(
    platform: SourcePlatform = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(ScrapedSource).order_by(desc(ScrapedSource.created_at))
    if platform:
        q = q.where(ScrapedSource.platform == platform)
    result  = await db.execute(q.limit(100))
    sources = result.scalars().all()
    active  = get_active_monitors()
    return [
        {
            "id":            str(s.id),
            "platform":      s.platform,
            "identifier":    s.identifier,
            "display_name":  s.display_name,
            "status":        s.status,
            "is_auto":       s.is_auto,
            "message_count": s.message_count,
            "last_scraped":  s.last_scraped,
            "is_monitoring": str(s.id) in active,
            "created_at":    s.created_at,
        }
        for s in sources
    ]


@router.delete("/sources/{source_id}", status_code=204)
async def delete_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("investigate:run")),
):
    await stop_monitor(str(source_id))
    result = await db.execute(select(ScrapedSource).where(ScrapedSource.id == source_id))
    source = result.scalar_one_or_none()
    if source:
        await db.delete(source)
        await db.commit()


# ── Scraping ──────────────────────────────────────────────────────────────────
@router.post("/sources/{source_id}/scrape")
async def scrape_source(
    source_id: UUID,
    limit: int = Query(50, le=200),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("investigate:run")),
):
    """Trigger immediate scrape of a source."""
    result = await db.execute(select(ScrapedSource).where(ScrapedSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        return JSONResponse(status_code=404, content={"error": "Source not found"})

    messages = []
    if source.platform == SourcePlatform.TELEGRAM:
        messages = await scrape_recent_messages(source.identifier, limit)

    # Store results
    stored = 0
    for msg in messages:
        analysis = msg.get("analysis") or analyze_content(msg.get("text",""), source.platform)
        content  = ExtractedContent(
            source_id    = source.id,
            platform     = source.platform,
            message_id   = msg.get("message_id"),
            content_text = msg.get("text",""),
            author       = msg.get("author"),
            category     = analysis["category"],
            risk_score   = analysis["risk_score"],
            is_flagged   = analysis["is_flagged"],
            raw_data     = {"demo": msg.get("demo", False)},
        )
        db.add(content)
        stored += 1

    source.last_scraped  = datetime.now(timezone.utc)
    source.message_count = (source.message_count or 0) + stored
    await db.commit()

    return {
        "source_id":       str(source_id),
        "messages_scraped":stored,
        "flagged":         sum(1 for m in messages if m.get("analysis",{}).get("is_flagged")),
        "status":          "completed",
    }


@router.post("/sources/{source_id}/monitor/start")
async def start_monitoring(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("investigate:run")),
):
    """Start real-time monitoring of a source."""
    result = await db.execute(select(ScrapedSource).where(ScrapedSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        return JSONResponse(status_code=404, content={"error": "Source not found"})

    async def on_message(msg: dict):
        from app.tasks.scraper_tasks import process_message_task
        msg["platform"] = source.platform
        process_message_task.delay(str(source_id), msg)

    success = await start_monitor(str(source_id), source.identifier, on_message)
    return {"status": "monitoring" if success else "error", "source_id": str(source_id)}


@router.post("/sources/{source_id}/monitor/stop")
async def stop_monitoring(
    source_id: UUID,
    current_user: User = Depends(require_perm("investigate:run")),
):
    stopped = await stop_monitor(str(source_id))
    return {"status": "stopped" if stopped else "not_running", "source_id": str(source_id)}


# ── Content ───────────────────────────────────────────────────────────────────
@router.get("/content")
async def list_content(
    source_id:  UUID    = Query(None),
    platform:   str     = Query(None),
    category:   str     = Query(None),
    flagged_only:bool   = Query(False),
    min_risk:   float   = Query(0),
    page:       int     = Query(1, ge=1),
    per_page:   int     = Query(20, le=100),
    db: AsyncSession    = Depends(get_db),
    current_user: User  = Depends(get_current_user),
):
    q = select(ExtractedContent).order_by(desc(ExtractedContent.scraped_at))
    if source_id:   q = q.where(ExtractedContent.source_id == source_id)
    if platform:    q = q.where(ExtractedContent.platform  == platform)
    if category:    q = q.where(ExtractedContent.category  == category)
    if flagged_only:q = q.where(ExtractedContent.is_flagged == True)
    if min_risk > 0:q = q.where(ExtractedContent.risk_score >= min_risk)

    total  = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    result = await db.execute(q.offset((page-1)*per_page).limit(per_page))
    items  = result.scalars().all()

    return {
        "content":  [
            {
                "id":           str(c.id),
                "source_id":    str(c.source_id),
                "platform":     c.platform,
                "content_text": (c.content_text or "")[:500],
                "author":       c.author,
                "category":     c.category,
                "risk_score":   c.risk_score,
                "is_flagged":   c.is_flagged,
                "scraped_at":   c.scraped_at,
            }
            for c in items
        ],
        "total":    total,
        "page":     page,
        "per_page": per_page,
    }


# ── Indicators ────────────────────────────────────────────────────────────────
@router.get("/indicators")
async def list_indicators(
    indicator_type: str   = Query(None),
    platform:       str   = Query(None),
    min_risk:       float = Query(0),
    search:         str   = Query(None),
    page:           int   = Query(1, ge=1),
    per_page:       int   = Query(20, le=100),
    db: AsyncSession      = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    q = select(ExtractedIndicator).order_by(desc(ExtractedIndicator.risk_score))
    if indicator_type: q = q.where(ExtractedIndicator.indicator_type == indicator_type)
    if platform:       q = q.where(ExtractedIndicator.platform       == platform)
    if min_risk > 0:   q = q.where(ExtractedIndicator.risk_score     >= min_risk)
    if search:         q = q.where(ExtractedIndicator.value.ilike(f"%{search}%"))

    total  = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    result = await db.execute(q.offset((page-1)*per_page).limit(per_page))
    items  = result.scalars().all()

    return {
        "indicators": [
            {
                "id":               str(i.id),
                "indicator_type":   i.indicator_type,
                "value":            i.value,
                "platform":         i.platform,
                "risk_score":       i.risk_score,
                "occurrence_count": i.occurrence_count,
                "context":          i.context,
                "first_seen":       i.first_seen,
            }
            for i in items
        ],
        "total": total, "page": page, "per_page": per_page,
    }


# ── Analyze text ──────────────────────────────────────────────────────────────
@router.post("/analyze")
async def analyze_text(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """Analyze any text for IOCs and risk scoring."""
    text     = payload.get("text", "")
    platform = payload.get("platform", "manual")
    result   = analyze_content(text, platform)
    return result


# ── OSINT tools ───────────────────────────────────────────────────────────────
@router.post("/osint/sherlock")
async def osint_sherlock(
    payload: dict,
    current_user: User = Depends(require_perm("investigate:run")),
):
    return await run_sherlock(payload.get("username",""))

@router.post("/osint/maigret")
async def osint_maigret(
    payload: dict,
    current_user: User = Depends(require_perm("investigate:run")),
):
    return await run_maigret(payload.get("username",""))

@router.post("/osint/holehe")
async def osint_holehe(
    payload: dict,
    current_user: User = Depends(require_perm("investigate:run")),
):
    return await run_holehe(payload.get("email",""))

@router.post("/osint/theharvester")
async def osint_harvester(
    payload: dict,
    current_user: User = Depends(require_perm("investigate:run")),
):
    return await run_theharvester(payload.get("domain",""), payload.get("sources","google,bing"))


# ── Stats ─────────────────────────────────────────────────────────────────────
@router.get("/stats")
async def scraper_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_sources  = (await db.execute(select(func.count(ScrapedSource.id)))).scalar() or 0
    active_sources = (await db.execute(select(func.count(ScrapedSource.id)).where(ScrapedSource.status == SourceStatus.ACTIVE))).scalar() or 0
    total_content  = (await db.execute(select(func.count(ExtractedContent.id)))).scalar() or 0
    flagged        = (await db.execute(select(func.count(ExtractedContent.id)).where(ExtractedContent.is_flagged == True))).scalar() or 0
    total_inds     = (await db.execute(select(func.count(ExtractedIndicator.id)))).scalar() or 0
    high_risk_inds = (await db.execute(select(func.count(ExtractedIndicator.id)).where(ExtractedIndicator.risk_score >= 70))).scalar() or 0

    by_platform = {}
    for p in SourcePlatform:
        cnt = (await db.execute(select(func.count(ExtractedContent.id)).where(ExtractedContent.platform == p))).scalar() or 0
        if cnt > 0:
            by_platform[p.value] = cnt

    by_category = {}
    for c in ContentCategory:
        cnt = (await db.execute(select(func.count(ExtractedContent.id)).where(ExtractedContent.category == c))).scalar() or 0
        if cnt > 0:
            by_category[c.value] = cnt

    return {
        "total_sources":       total_sources,
        "active_sources":      active_sources,
        "total_content":       total_content,
        "flagged_content":     flagged,
        "total_indicators":    total_inds,
        "high_risk_indicators":high_risk_inds,
        "active_monitors":     len(get_active_monitors()),
        "by_platform":         by_platform,
        "by_category":         by_category,
    }


# ── Correlation ───────────────────────────────────────────────────────────────
@router.get("/correlation/{value}")
async def correlate_indicator(
    value: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Find the same IOC across all platforms."""
    result = await db.execute(
        select(ExtractedIndicator).where(
            ExtractedIndicator.value.ilike(f"%{value}%")
        ).order_by(desc(ExtractedIndicator.risk_score)).limit(50)
    )
    indicators = result.scalars().all()

    platforms = list(set(i.platform for i in indicators))
    nodes, edges = [], []

    # Centre node for the indicator
    nodes.append({"id": "target", "label": value[:30], "type": "indicator", "color": "#EF4444"})

    # Platform nodes
    for p in platforms:
        nodes.append({"id": p, "label": p.upper(), "type": "platform", "color": "#3B82F6"})
        edges.append({"from": "target", "to": p, "label": "found_on"})

    # Source nodes
    seen_sources = set()
    for ind in indicators:
        sid = str(ind.source_id)
        if sid not in seen_sources:
            seen_sources.add(sid)
            nodes.append({"id": sid, "label": f"Source {sid[:8]}", "type": "source", "color": "#10B981"})
            edges.append({"from": str(ind.platform), "to": sid, "label": "in_source"})

    return {
        "value":      value,
        "platforms":  [p.value for p in platforms],
        "occurrences":len(indicators),
        "nodes":      nodes,
        "edges":      edges,
        "is_cross_platform": len(platforms) > 1,
        "indicators": [
            {"id": str(i.id), "type": i.indicator_type, "platform": i.platform,
             "risk_score": i.risk_score, "first_seen": i.first_seen}
            for i in indicators[:10]
        ],
    }


# ── Internet Scam Scraper ─────────────────────────────────────────────────────
from app.modules.net_scrapper.services.internet_scraper import (
    scrape_internet_for_scams, scrape_url_for_scam
)

@router.post("/internet/scan")
async def internet_scan(
    payload: dict = {},
    current_user: User = Depends(require_perm("investigate:run")),
):
    """
    Scan the internet for scam content.
    Searches DuckDuckGo, Google News, Reddit, Twitter for all scam types.
    """
    scam_types     = payload.get("scam_types", None)
    max_per_query  = min(payload.get("max_per_query", 5), 10)
    include_reddit = payload.get("include_reddit", True)
    include_news   = payload.get("include_news",   True)
    include_twitter= payload.get("include_twitter", True)

    results = await scrape_internet_for_scams(
        scam_types=scam_types,
        max_per_query=max_per_query,
        include_reddit=include_reddit,
        include_news=include_news,
        include_twitter=include_twitter,
    )
    flagged    = [r for r in results if r["is_flagged"]]
    high_risk  = [r for r in results if r["risk_score"] >= 70]
    by_type    = {}
    for r in results:
        t = r["scam_type"]
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "total":       len(results),
        "flagged":     len(flagged),
        "high_risk":   len(high_risk),
        "by_scam_type":by_type,
        "results":     results[:100],
        "scraped_at":  datetime.now(timezone.utc).isoformat(),
    }


@router.post("/internet/scan-url")
async def scan_single_url(
    payload: dict,
    current_user: User = Depends(require_perm("investigate:run")),
):
    """Analyze a specific URL for scam content."""
    url = payload.get("url","")
    if not url:
        return JSONResponse(status_code=400, content={"error": "URL required"})
    return await scrape_url_for_scam(url)


@router.get("/internet/scam-types")
async def get_scam_types(current_user: User = Depends(get_current_user)):
    """List all supported scam types."""
    from app.modules.net_scrapper.services.internet_scraper import SCAM_QUERIES
    return [
        {"id": k, "label": k.replace("_"," ").title(), "queries": len(v)}
        for k, v in SCAM_QUERIES.items()
    ]


# ── URL Flagging endpoints ─────────────────────────────────────────────────

@router.post("/urls/analyze")
async def analyze_urls_in_text(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """Extract and analyze all URLs found in a given text/message."""
    from app.modules.net_scrapper.services.url_flagger import process_message_for_urls
    text        = payload.get("text", "")
    source_info = payload.get("source", {})
    if not text:
        return {"error": "text required"}
    return process_message_for_urls(text, source_info)


@router.post("/urls/enrich")
async def enrich_url(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """Deep-scan a single URL via VirusTotal + local analysis."""
    from app.modules.net_scrapper.services.url_flagger import analyze_url, enrich_with_virustotal
    url = payload.get("url", "")
    if not url:
        return {"error": "url required"}
    base = analyze_url(url)
    vt   = await enrich_with_virustotal(url)
    return {**base, "virustotal": vt}


@router.post("/urls/add-to-monitoring")
async def add_url_to_monitoring(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Officer decision: add a flagged URL/domain as a new monitored source."""
    from app.modules.net_scrapper.models import ScrapedSource, SourcePlatform, SourceStatus
    url      = payload.get("url", "")
    notes    = payload.get("notes", "")
    approved = payload.get("approved", True)

    if not approved:
        return {"status": "dismissed", "message": "URL dismissed by officer"}

    from urllib.parse import urlparse
    parsed   = urlparse(url if url.startswith('http') else f'https://{url}')
    domain   = parsed.netloc.replace('www.', '')
    is_tg    = domain in ('t.me', 'telegram.me')
    platform = SourcePlatform.TELEGRAM if is_tg else SourcePlatform.WEB

    source = ScrapedSource(
        name        = f"Flagged: {domain}",
        platform    = platform,
        identifier  = url,
        description = f"Auto-flagged from channel monitoring. Officer notes: {notes}",
        status      = SourceStatus.ACTIVE,
        added_by_id = current_user.id,
        auto_monitor= True,
        keywords    = [],
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    return {
        "status":    "added",
        "source_id": str(source.id),
        "platform":  platform,
        "message":   f"Now monitoring {domain}",
    }


@router.get("/urls/flagged")
async def get_flagged_urls(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all sources that were added via URL flagging (auto-flagged)."""
    from sqlalchemy import select
    from app.modules.net_scrapper.models import ScrapedSource
    result = await db.execute(
        select(ScrapedSource)
        .where(ScrapedSource.description.like('%Auto-flagged%'))
        .order_by(ScrapedSource.created_at.desc())
        .limit(limit)
    )
    sources = result.scalars().all()
    return [
        {
            "id":         str(s.id),
            "name":       s.name,
            "identifier": s.identifier,
            "platform":   s.platform,
            "status":     s.status,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in sources
    ]


# ── Channel Redirect Detection ─────────────────────────────────────────────

@router.post("/channels/detect-redirect")
async def detect_channel_redirect(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """
    Analyze a message for channel redirect/migration signals.
    Returns detected channels and whether officer action is needed.
    """
    from app.modules.net_scrapper.services.channel_redirect_detector import (
        detect_channel_redirects, build_redirect_alert
    )
    text        = payload.get("text", "")
    source_id   = payload.get("source_id", "unknown")
    source_name = payload.get("source_name", "Unknown Channel")

    if not text:
        return {"error": "text required"}

    redirect_data = detect_channel_redirects(text)
    alert         = build_redirect_alert(text, source_id, source_name, redirect_data)

    return {
        "redirect_analysis": redirect_data,
        "alert":             alert,
        "has_alert":         alert is not None,
    }


@router.post("/channels/add-redirect-target")
async def add_redirect_target(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Officer approved: add a detected redirect target channel to monitoring.
    Also records the parent → child relationship.
    """
    from app.modules.net_scrapper.models import ScrapedSource, SourcePlatform, SourceStatus

    channel_value  = payload.get("channel_value", "")   # e.g. "newscam123" or "t.me/+abc"
    channel_type   = payload.get("channel_type", "username")  # invite_link | username
    parent_source  = payload.get("parent_source_name", "Unknown")
    parent_id      = payload.get("parent_source_id", "")
    approved       = payload.get("approved", True)
    notes          = payload.get("notes", "")

    if not approved:
        return {"status": "dismissed", "message": "Redirect target dismissed by officer"}

    # Build the identifier
    if channel_type == "invite_link":
        identifier = channel_value if channel_value.startswith('http') \
                     else f'https://{channel_value}'
        name = f"Redirect target (invite): {channel_value[:30]}"
    else:
        identifier = f"@{channel_value}"
        name       = f"Redirect target: @{channel_value}"

    source = ScrapedSource(
        name         = name,
        platform     = SourcePlatform.TELEGRAM,
        identifier   = identifier,
        description  = (
            f"Auto-detected redirect from '{parent_source}' (id:{parent_id}). "
            f"Officer approved monitoring. Notes: {notes}"
        ),
        status       = SourceStatus.ACTIVE,
        added_by_id  = current_user.id,
        auto_monitor = True,
        keywords     = [],
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    return {
        "status":      "added",
        "source_id":   str(source.id),
        "identifier":  identifier,
        "parent":      parent_source,
        "message":     f"Now monitoring redirect target: {identifier}",
        "chain_note":  f"{parent_source} → {identifier}",
    }


@router.get("/channels/redirect-chain")
async def get_redirect_chain(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all channels that were added as redirect targets — visualize the chain."""
    from sqlalchemy import select
    from app.modules.net_scrapper.models import ScrapedSource
    result = await db.execute(
        select(ScrapedSource)
        .where(ScrapedSource.description.like('%Auto-detected redirect%'))
        .order_by(ScrapedSource.created_at.asc())
    )
    sources = result.scalars().all()

    chain_nodes = []
    chain_edges = []
    seen_parents = set()

    for s in sources:
        desc = s.description or ""
        # Parse parent from description
        import re
        m = re.search(r"from '([^']+)'", desc)
        parent_name = m.group(1) if m else "Unknown"

        chain_nodes.append({
            "id":         str(s.id),
            "label":      s.identifier,
            "name":       s.name,
            "status":     str(s.status),
            "created_at": s.created_at.isoformat() if s.created_at else "",
        })

        if parent_name not in seen_parents:
            seen_parents.add(parent_name)
            chain_nodes.append({
                "id":    f"parent_{parent_name}",
                "label": parent_name,
                "name":  parent_name,
                "is_parent": True,
            })

        chain_edges.append({
            "from":  f"parent_{parent_name}",
            "to":    str(s.id),
            "label": "redirected_to",
        })

    return {
        "total":  len(sources),
        "nodes":  chain_nodes,
        "edges":  chain_edges,
        "chains": [{"parent": e["from"].replace("parent_",""), "child": e["to"]} for e in chain_edges],
    }
