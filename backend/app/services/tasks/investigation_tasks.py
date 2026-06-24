from app.core.celery_app import celery_app
import structlog
logger = structlog.get_logger(__name__)

@celery_app.task(bind=True, name="investigation_tasks.run")
def run_investigation(self, investigation_id: str, inv_type: str, query: str, query_type: str):
    logger.info("Celery investigation", id=investigation_id, type=inv_type)
    return {"investigation_id": investigation_id, "status": "completed"}
