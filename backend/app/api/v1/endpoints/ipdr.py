"""
IPDR (IP Detail Record) Analysis Tool
Extracts IPv4/IPv6 addresses from uploaded PDF and enriches with GeoIP data.
Standard law enforcement tool used under Section 91 CrPC.
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
    r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
)
IPV6_PATTERN = re.compile(
    r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|'
    r'\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b|'
    r'\b::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}\b|'
    r'\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b'
)

# Private/reserved ranges to filter out
PRIVATE_PREFIXES = [
    "10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
    "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
    "127.", "0.", "169.254.", "255.", "224.", "240.",
]

def _is_private(ip: str) -> bool:
    return any(ip.startswith(p) for p in PRIVATE_PREFIXES)

def _extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(
                page.extract_text() or ""
                for page in pdf.pages
            )
    except ImportError:
        pass

    # Fallback: PyPDF2
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )
    except ImportError:
        pass

    # Last resort: raw text extraction
    text = content.decode("latin-1", errors="ignore")
    printable = re.sub(r'[^\x20-\x7E\n\r\t]', ' ', text)
    return re.sub(r'\s+', ' ', printable)


def _extract_ips(text: str) -> dict[str, list[str]]:
    """Extract and deduplicate IPv4 and IPv6 from text."""
    ipv4_all = IPV4_PATTERN.findall(text)
    ipv6_all = IPV6_PATTERN.findall(text)

    # Deduplicate, filter private
    ipv4_public   = list(dict.fromkeys(ip for ip in ipv4_all if not _is_private(ip)))
    ipv4_private  = list(dict.fromkeys(ip for ip in ipv4_all if _is_private(ip)))
    ipv6_public   = list(dict.fromkeys(ipv6_all))

    return {
        "ipv4_public":  ipv4_public,
        "ipv4_private": ipv4_private,
        "ipv6":         ipv6_public,
    }


async def _enrich_ip_batch(ips: list[str], token: str = "") -> list[dict]:
    """Batch enrich IPs using IPinfo API."""
    results = []

    # Use IPinfo batch API if token available
    if token and len(ips) > 0:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                resp = await c.post(
                    f"https://ipinfo.io/batch?token={token}",
                    json=ips[:500],   # IPinfo batch limit
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for ip, info in data.items():
                        if isinstance(info, dict):
                            results.append(_format_ip_info(ip, info))
                    return results
        except Exception:
            pass

    # Fallback: individual lookups (rate limited)
    async def _lookup_one(ip: str) -> dict:
        try:
            params = {"token": token} if token else {}
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(f"https://ipinfo.io/{ip}/json", params=params)
                if r.status_code == 200:
                    return _format_ip_info(ip, r.json())
        except Exception:
            pass
        return _format_ip_info(ip, {})

    # Process in batches of 10 concurrent
    for i in range(0, min(len(ips), 100), 10):
        batch   = ips[i:i+10]
        batch_results = await asyncio.gather(*[_lookup_one(ip) for ip in batch])
        results.extend(batch_results)
        if i + 10 < len(ips):
            await asyncio.sleep(0.5)   # Rate limit respect

    return results


def _format_ip_info(ip: str, info: dict) -> dict:
    """Format IPinfo response into standardised structure."""
    org      = info.get("org", "")
    asn      = org.split()[0] if org and org.split()[0].startswith("AS") else ""
    isp      = " ".join(org.split()[1:]) if org else ""
    loc      = info.get("loc", "")
    lat, lon = (loc.split(",") + ["", ""])[:2] if loc else ("", "")

    # Risk indicators
    is_tor   = info.get("privacy", {}).get("tor",   False) if "privacy" in info else False
    is_vpn   = info.get("privacy", {}).get("vpn",   False) if "privacy" in info else False
    is_proxy = info.get("privacy", {}).get("proxy", False) if "privacy" in info else False
    is_hosting=info.get("privacy", {}).get("hosting",False) if "privacy" in info else False

    risk_score = 0
    if is_tor:     risk_score += 40
    if is_vpn:     risk_score += 20
    if is_proxy:   risk_score += 15
    if is_hosting: risk_score += 10

    flags = []
    if is_tor:      flags.append("TOR EXIT NODE")
    if is_vpn:      flags.append("VPN")
    if is_proxy:    flags.append("PROXY")
    if is_hosting:  flags.append("HOSTING/DATACENTER")

    return {
        "ip":           ip,
        "version":      "IPv6" if ":" in ip else "IPv4",
        "hostname":     info.get("hostname", ""),
        "city":         info.get("city",     ""),
        "region":       info.get("region",   ""),
        "country":      info.get("country",  ""),
        "country_name": info.get("country",  ""),
        "org":          org,
        "asn":          asn,
        "isp":          isp,
        "timezone":     info.get("timezone", ""),
        "latitude":     lat,
        "longitude":    lon,
        "postal":       info.get("postal",   ""),
        "is_tor":       is_tor,
        "is_vpn":       is_vpn,
        "is_proxy":     is_proxy,
        "is_hosting":   is_hosting,
        "flags":        flags,
        "risk_score":   risk_score,
        "severity":     "CRITICAL" if risk_score >= 40 else "HIGH" if risk_score >= 20 else "MEDIUM" if risk_score >= 10 else "LOW",
        "google_maps":  f"https://maps.google.com/?q={lat},{lon}" if lat and lon else "",
        "raw":          info,
    }


@router.post("/analyze-pdf")
async def analyze_ipdr_pdf(
    file:        UploadFile = File(...),
    include_private: bool  = Form(False),
    max_ips:     int       = Form(500),
    current_user: User = Depends(require_perm("investigate:run")),
):
    """
    Upload an IPDR PDF and extract + enrich all IP addresses.
    Standard LEA tool used under Section 91 CrPC.
    """
    # Validate file
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "Only PDF files supported"})

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:   # 50MB limit
        return JSONResponse(status_code=413, content={"error": "File too large (max 50MB)"})

    # Extract text
    text = _extract_text_from_pdf(content)
    if not text.strip():
        return JSONResponse(status_code=422, content={"error": "Could not extract text from PDF"})

    # Extract IPs
    extracted = _extract_ips(text)
    public_ips  = extracted["ipv4_public"][:max_ips]
    private_ips = extracted["ipv4_private"]
    ipv6_ips    = extracted["ipv6"][:50]

    all_to_enrich = public_ips + (ipv6_ips[:20])

    # Enrich with GeoIP
    token   = settings.IPINFO_TOKEN or ""
    enriched = await _enrich_ip_batch(all_to_enrich, token)

    # Summary stats
    countries = {}
    isps      = {}
    high_risk = []
    for ip_data in enriched:
        c = ip_data.get("country", "Unknown") or "Unknown"
        countries[c] = countries.get(c, 0) + 1
        isp = ip_data.get("isp", "Unknown") or "Unknown"
        if isp:
            isps[isp] = isps.get(isp, 0) + 1
        if ip_data.get("risk_score", 0) >= 20:
            high_risk.append(ip_data["ip"])

    return {
        "filename":         file.filename,
        "file_size":        len(content),
        "extracted_at":     datetime.now(timezone.utc).isoformat(),
        "extracted_by":     current_user.badge_number,
        "text_length":      len(text),
        "summary": {
            "total_ipv4_found":    len(extracted["ipv4_public"]) + len(extracted["ipv4_private"]),
            "public_ipv4":         len(extracted["ipv4_public"]),
            "private_ipv4":        len(extracted["ipv4_private"]),
            "ipv6_found":          len(extracted["ipv6"]),
            "unique_countries":    len(countries),
            "unique_isps":         len(isps),
            "high_risk_ips":       len(high_risk),
            "enriched_count":      len(enriched),
        },
        "top_countries":   dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]),
        "top_isps":        dict(sorted(isps.items(),     key=lambda x: x[1], reverse=True)[:10]),
        "high_risk_ips":   high_risk,
        "ip_details":      enriched,
        "private_ips":     private_ips[:50] if include_private else [],
        "ipv6_addresses":  extracted["ipv6"],
    }


@router.post("/analyze-text")
async def analyze_ipdr_text(
    payload: dict,
    current_user: User = Depends(require_perm("investigate:run")),
):
    """Analyze raw text pasted from IPDR — for copy-paste input."""
    text    = payload.get("text", "")
    max_ips = min(payload.get("max_ips", 200), 500)

    if not text.strip():
        return JSONResponse(status_code=400, content={"error": "Text is required"})

    extracted   = _extract_ips(text)
    public_ips  = extracted["ipv4_public"][:max_ips]
    token       = settings.IPINFO_TOKEN or ""
    enriched    = await _enrich_ip_batch(public_ips, token)

    return {
        "source":       "text_input",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "public_ipv4":  len(public_ips),
            "private_ipv4": len(extracted["ipv4_private"]),
            "ipv6_found":   len(extracted["ipv6"]),
            "enriched":     len(enriched),
        },
        "ip_details":   enriched,
    }
