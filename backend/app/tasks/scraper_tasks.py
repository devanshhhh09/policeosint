"""
Celery background tasks for Net Scrapper module
"""
from app.core.celery_app import celery_app
import structlog

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="scraper.process_message")
def process_message_task(self, source_id: str, message_data: dict):
    """Process and store a scraped message."""
    import asyncio
    from app.core.database import AsyncSessionLocal
    from app.modules.net_scrapper.models import (
        ExtractedContent, ExtractedIndicator,
        ContentCategory, SourcePlatform, IndicatorType
    )
    from app.modules.net_scrapper.services.content_analyzer import analyze_content
    import uuid

    async def _process():
        async with AsyncSessionLocal() as db:
            text     = message_data.get("text", "")
            platform = message_data.get("platform", "telegram")
            analysis = analyze_content(text, platform)

            content = ExtractedContent(
                source_id    = uuid.UUID(source_id),
                platform     = SourcePlatform(platform),
                message_id   = message_data.get("message_id"),
                content_text = text,
                author       = message_data.get("author"),
                category     = analysis["category"],
                risk_score   = analysis["risk_score"],
                is_flagged   = analysis["is_flagged"],
                raw_data     = message_data,
            )
            db.add(content)
            await db.flush()

            # Store indicators
            for ind in analysis.get("indicators", []):
                db.add(ExtractedIndicator(
                    source_id      = uuid.UUID(source_id),
                    content_id     = content.id,
                    indicator_type = IndicatorType(ind["type"]),
                    value          = ind["value"],
                    platform       = SourcePlatform(platform),
                    risk_score     = ind.get("risk_score", 0.0),
                    context        = ind.get("context", ""),
                ))

            await db.commit()
            logger.info("Message processed", source_id=source_id, risk=analysis["risk_score"])

    asyncio.run(_process())
    return {"status": "processed", "source_id": source_id}


@celery_app.task(name="scraper.run_osint_tool")
def run_osint_tool_task(tool: str, target: str) -> dict:
    """Run OSINT CLI tool in background."""
    import asyncio
    from app.modules.net_scrapper.services.osint_orchestrator import (
        run_sherlock, run_maigret, run_holehe, run_theharvester
    )
    tool_map = {
        "sherlock":      run_sherlock,
        "maigret":       run_maigret,
        "holehe":        run_holehe,
        "theharvester":  run_theharvester,
    }
    fn = tool_map.get(tool)
    if not fn:
        return {"error": f"Unknown tool: {tool}"}
    return asyncio.run(fn(target))


@celery_app.task(name="scraper.auto_monitor_tick")
def auto_monitor_tick():
    """Periodic task to check auto-monitored sources."""
    logger.info("Auto monitor tick running")
    return {"status": "ok"}
