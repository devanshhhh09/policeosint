import time, structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger(__name__)
SKIP = {"/health", "/", "/api/docs", "/api/redoc", "/api/openapi.json"}

class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in SKIP:
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        logger.info("request", method=request.method, path=request.url.path,
                    status=response.status_code,
                    ms=round((time.perf_counter()-start)*1000, 1))
        return response
