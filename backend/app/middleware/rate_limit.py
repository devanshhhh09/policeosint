"""Rate limiting middleware — Phase 7"""
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Simple in-memory rate limiter (use Redis in production)
_request_counts: dict = defaultdict(list)
RATE_LIMIT = 60   # requests per minute
WINDOW     = 60   # seconds

SKIP_PATHS = {"/health", "/", "/api/docs", "/api/redoc", "/api/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        # Get client IP
        ip  = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old requests outside window
        _request_counts[ip] = [t for t in _request_counts[ip] if now - t < WINDOW]

        if len(_request_counts[ip]) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Max 60 requests/minute.", "code": "RATE_LIMITED"},
                headers={"Retry-After": "60", "X-RateLimit-Limit": str(RATE_LIMIT)},
            )

        _request_counts[ip].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(RATE_LIMIT - len(_request_counts[ip]))
        return response
