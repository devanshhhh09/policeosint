from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, cases, dashboard, audit,
    investigations, ai, graph, cluster,
    reports, evidence, manual,
)

api_router = APIRouter()
api_router.include_router(auth.router,           prefix="/auth",           tags=["Auth"])
api_router.include_router(cases.router,          prefix="/cases",          tags=["Cases"])
api_router.include_router(dashboard.router,      prefix="/dashboard",      tags=["Dashboard"])
api_router.include_router(audit.router,          prefix="/audit",          tags=["Audit"])
api_router.include_router(investigations.router, prefix="/investigations", tags=["Investigations"])
api_router.include_router(ai.router,             prefix="/ai",             tags=["AI Copilot"])
api_router.include_router(graph.router,          prefix="/graph",          tags=["Entity Graph"])
api_router.include_router(cluster.router,        prefix="/cluster",        tags=["UPI Cluster"])
api_router.include_router(reports.router,        prefix="/reports",        tags=["Reports"])
api_router.include_router(evidence.router,       prefix="/evidence",       tags=["Evidence"])
api_router.include_router(manual.router,         prefix="/manual",         tags=["User Manual"])

# Net Scrapper module — added as isolated add-on
from app.modules.net_scrapper.api.endpoints import router as scrapper_router
api_router.include_router(scrapper_router, prefix="/scrapper", tags=["Net Scrapper"])

from app.api.v1.endpoints.ipdr import router as ipdr_router
api_router.include_router(ipdr_router, prefix="/ipdr", tags=["IPDR Analysis"])
