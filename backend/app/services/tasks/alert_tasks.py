from app.core.celery_app import celery_app
import structlog
logger = structlog.get_logger(__name__)

@celery_app.task(name="alert_tasks.check_dark_web")
def check_dark_web():
    logger.info("Dark web check running")

@celery_app.task(name="alert_tasks.refresh_threat_feeds")
def refresh_threat_feeds():
    logger.info("Threat feed refresh running")
