"""
IPDR (Internet Protocol Detail Record) Analyzer
Extracts IPv4/IPv6 from uploaded PDFs and enriches with GeoIP data.
Standard LEA tool — used under Section 91 CrPC for court-ordered IP records.
"""
import re, io, asyncio, hashlib
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
import httpx

from app.db.models.user import User
from app.api.deps import get_current_user, require_perm
from app.core.config import settings

router = APIRouter()

# ── Regex patterns ─────────────────────────────────────────────────────────────
IPV4_PATTERN = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
)
IPV6_PATTERN = re.compile(
    r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'
    r'|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b'
    r'|\b::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}\b'
    r'|\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b'
)

# IPs to skip (private, loopback, reserved)
SKIP_RANGES = [
    re.compile(r'^10\.'),
    re.compile(r'^172\.(1[6-9]|2\d|3[01])\.'),
    re.compile(r'^192\.168\.'),
    re.compile(r'^127\.'),
    re.compile(r'^0\.'),
    re.compile(r'^169\.254\.'),
    re.compile(r'^255\.'),
    re.compile(r'^224\.'),
    re.compile(r'^::1$'),
    re.compile(r'^fc'),
    re.compile(r'^fd'),
    re.compile(r'^fe80'),
]

def _is_private(ip: str) -> bool:
    return any(p.match(ip.lower()) for p in SKIP_RANGES)


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text   = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except ImportError:
        pass
    try:
        import pdfminer.high_level as pdfminer
        return pdfminer.extract_text(io.BytesIO(pdf_bytes))
    except ImportError:
        pass
    # Last resort: raw text extraction
    text = pdf_bytes.decode("utf-8", errors="ignore")
    return text


def _extract_ips(text: str) -> dict[str, list[str]]:
    """Extract all unique IPs from text, separated by version."""
    ipv4s = list(dict.fromkeys(
        ip for ip in IPV4_PATTERN.findall(text)
        if not _is_private(ip)
    ))
    ipv6s = list(dict.fromkeys(
        ip for ip in IPV6_PATTERN.findall(text)
        if not _is_private(ip)
    ))
    return {"ipv4": ipv4s, "ipv6": ipv6s}


async def _lookup_ip(ip: str, session: httpx.AsyncClient) -> dict[str, Any]:
    """Look up a single IP via IPinfo."""
    result: dict[str, Any] = {
        "ip":       ip,
        "version":  "IPv6" if ":" in ip else "IPv4",
        "status":   "pending",
    }
    try:
        params = {"token": settings.IPINFO_TOKEN} if settings.IPINFO_TOKEN else {}
        resp   = await session.get(
            f"https://ipinfo.io/{ip}/json",
            params=params,
            timeout=8,
        )
        if resp.status_code == 200:
            d   = resp.json()
            org = d.get("org", "")
            result.update({
                "status":    "found",
                "hostname":  d.get("hostname", ""),
                "city":      d.get("city",     ""),
                "region":    d.get("region",   ""),
                "country":   d.get("country",  ""),
                "org":       org,
                "asn":       org.split()[0] if org else "",
                "isp":       " ".join(org.split()[1:]) if org else "",
                "timezone":  d.get("timezone", ""),
                "loc":       d.get("loc",      ""),
                "postal":    d.get("postal",   ""),
                "is_vpn":    d.get("privacy",  {}).get("vpn",   False),
                "is_proxy":  d.get("privacy",  {}).get("proxy", False),
                "is_tor":    d.get("privacy",  {}).get("tor",   False),
                "abuse_contact": d.get("abuse", {}).get("email", ""),
                "google_maps": f"https://maps.google.com/maps?q={d.get('loc','')}" if d.get("loc") else "",
            })
            # Risk scoring
            risk = 0
            if result.get("is_tor"):   risk += 40
            if result.get("is_proxy"): risk += 25
            if result.get("is_vpn"):   risk += 20
            if result.get("country") not in ("IN", ""):
                risk += 15  # Foreign IP in Indian IPDR
            result["risk_score"] = min(risk, 100)
            result["risk_label"] = (
                "HIGH"   if risk >= 60 else
                "MEDIUM" if risk >= 30 else "LOW"
            )
        else:
            result["status"] = "not_found"
    except Exception as e:
        result["status"] = "error"
        result["error"]  = str(e)
    return result


@router.post("/analyze")
async def analyze_ipdr(
    file:         UploadFile = File(...),
    include_private: bool    = Form(False),
    current_user: User       = Depends(require_perm("investigate:run")),
):
    """
    Upload an IPDR PDF. Extracts all IPv4/IPv6 addresses,
    enriches with GeoIP, ISP, ASN, and risk scoring.
    """
    # Validate file
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "Only PDF files supported"})

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 50 * 1024 * 1024:
        return JSONResponse(status_code=413, content={"error": "File too large — max 50MB"})

    # Extract text
    text = _extract_text_from_pdf(pdf_bytes)
    if not text.strip():
        return JSONResponse(status_code=422, content={"error": "Could not extract text from PDF"})

    # Extract IPs
    ips     = _extract_ips(text)
    all_ips = ips["ipv4"] + ips["ipv6"]

    if not all_ips:
        return JSONResponse(status_code=404, content={
            "error": "No public IP addresses found in the PDF",
            "tip":   "Ensure the PDF contains IP address logs in standard format",
        })

    # Enrich all IPs concurrently (max 50)
    all_ips = all_ips[:50]
    async with httpx.AsyncClient() as session:
        tasks   = [_lookup_ip(ip, session) for ip in all_ips]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    enriched = []
    for r in results:
        if isinstance(r, dict):
            enriched.append(r)

    # Summary stats
    countries = {}
    isps      = {}
    for r in enriched:
        c = r.get("country", "Unknown") or "Unknown"
        i = r.get("isp",     "Unknown") or "Unknown"
        countries[c] = countries.get(c, 0) + 1
        isps[i]      = isps.get(i, 0) + 1

    high_risk = [r for r in enriched if r.get("risk_score", 0) >= 60]
    foreign   = [r for r in enriched if r.get("country","") not in ("IN","")]
    tor_vpn   = [r for r in enriched if r.get("is_tor") or r.get("is_proxy") or r.get("is_vpn")]

    return {
        "filename":       file.filename,
        "file_size":      len(pdf_bytes),
        "text_length":    len(text),
        "analyzed_at":    datetime.now(timezone.utc).isoformat(),
        "analyzed_by":    current_user.badge_number,
        "summary": {
            "total_ips_found":   len(all_ips),
            "ipv4_count":        len(ips["ipv4"]),
            "ipv6_count":        len(ips["ipv6"]),
            "successfully_enriched": len(enriched),
            "high_risk_count":   len(high_risk),
            "foreign_ips":       len(foreign),
            "tor_vpn_proxy":     len(tor_vpn),
            "unique_countries":  len(countries),
            "unique_isps":       len(isps),
            "top_countries":     dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:8]),
            "top_isps":          dict(sorted(isps.items(),      key=lambda x: x[1], reverse=True)[:8]),
        },
        "results": enriched,
        "high_risk_ips": high_risk,
    }


@router.post("/lookup")
async def lookup_single_ip(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """Look up a single IP address."""
    ip = payload.get("ip","").strip()
    if not ip:
        return JSONResponse(status_code=400, content={"error": "IP address required"})
    async with httpx.AsyncClient() as session:
        return await _lookup_ip(ip, session)
