"""
PoliceOSINT — Main Application
AI-Powered Cyber Crime Investigation Platform
GPCSSI · Gurugram Cyber Cell · Phase 7
"""
from contextlib import asynccontextmanager
import time, os, logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import structlog

from app.core.config import settings
from app.core.database import engine, Base
from app.core.exceptions import PoliceOSINTException
from app.api.v1.router import api_router
from app.middleware.audit import AuditLogMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import SecurityHeadersMiddleware

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else 'INFO'))
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PoliceOSINT starting",
                env=settings.APP_ENV,
                version="1.0.0",
                platform="GPCSSI Gurugram")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")
    os.makedirs(settings.EVIDENCE_UPLOAD_DIR, exist_ok=True)
    logger.info("Evidence directory ready", path=settings.EVIDENCE_UPLOAD_DIR)
    yield
    await engine.dispose()
    logger.info("PoliceOSINT stopped cleanly")


app = FastAPI(
    title="PoliceOSINT API",
    description="""
## AI-Powered Cyber Crime Investigation Platform

Built for **GPCSSI · Gurugram Cyber Cell · Haryana Police**

### Features
- 10 OSINT investigation modules (Identity, IP, Domain, UPI, Crypto, Threat, Dark Web, GEOINT, Social, Media)
- AI-powered investigation copilot
- PDF report generation (FIR Support, Intelligence, Suspect Profile)
- Digital evidence management with SHA256 chain of custody
- Entity relationship graph
- UPI fraud cluster analysis
- MITRE ATT&CK threat mapping

### Authentication
All endpoints require JWT Bearer token. Login at `/api/v1/auth/login`.

### Roles
`super_admin` > `commissioner` > `sp` > `inspector` > `sub_inspector` > `constable` > `analyst` > `trainee`
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    contact={"name": "GPCSSI", "email": "cyber@haryana.gov.in"},
    license_info={"name": "Law Enforcement Use Only"},
)

# ── Middleware (order matters — outermost first) ───────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(AuditLogMiddleware)


# ── Request timing ─────────────────────────────────────────────────────────────
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start    = time.perf_counter()
    response = await call_next(request)
    ms       = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Process-Time-Ms"] = str(ms)
    return response


# ── Exception handlers ─────────────────────────────────────────────────────────
@app.exception_handler(PoliceOSINTException)
async def osint_exception_handler(request: Request, exc: PoliceOSINTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": exc.error_code},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"error": "Not found", "path": str(request.url.path)})


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error("Unhandled error", error=str(exc), path=str(request.url.path))
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")

# Static files for evidence (authenticated separately)
os.makedirs("evidence", exist_ok=True)
app.mount("/evidence", StaticFiles(directory="evidence"), name="evidence")


# ── Health + Info endpoints ────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {
        "status":   "operational",
        "platform": "PoliceOSINT",
        "version":  "1.0.0",
        "env":      settings.APP_ENV,
        "modules":  [
            "identity","ip","domain","upi_fraud","crypto",
            "threat","dark_web","geoint","social","media"
        ],
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message":  "PoliceOSINT API",
        "version":  "1.0.0",
        "docs":     "/api/docs",
        "health":   "/health",
        "platform": "GPCSSI · Gurugram Cyber Cell",
    }
