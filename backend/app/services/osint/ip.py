"""
IP Intelligence Service — Phase 2
Sources: IPinfo · Shodan · VirusTotal · AbuseIPDB
"""
import asyncio, re
from typing import Any
import httpx
from app.core.config import settings

PRIVATE = [r"^10\.", r"^172\.(1[6-9]|2\d|3[01])\.",
           r"^192\.168\.", r"^127\.", r"^0\.", r"^169\.254\."]

def _is_private(ip: str) -> bool:
    return any(re.match(p, ip) for p in PRIVATE)


async def investigate_ip(ip: str) -> dict[str, Any]:
    ip = ip.strip()
    if _is_private(ip):
        return {"ip": ip, "risk_score": 0,
                "sources": {"error": {"message": f"{ip} is a private IP — not publicly routable"}},
                "summary": "Private IP address"}

    tasks = [_ipinfo(ip), _virustotal(ip)]
    if settings.SHODAN_API_KEY:
        tasks.append(_shodan(ip))

    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    sources: dict[str, Any] = {}
    for r in gathered:
        if isinstance(r, dict):
            sources.update(r)

    risk = _calc_risk(sources)
    return {"ip": ip, "risk_score": risk,
            "sources": sources, "summary": _build_summary(ip, sources, risk)}


async def _ipinfo(ip: str) -> dict:
    src: dict[str, Any] = {"ipinfo": {"name": "IPinfo / GeoIP"}}
    try:
        params = {"token": settings.IPINFO_TOKEN} if settings.IPINFO_TOKEN else {}
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://ipinfo.io/{ip}/json", params=params)
            if r.status_code == 200:
                d = r.json()
                org   = d.get("org", "")
                asn   = org.split()[0] if org else ""
                isp   = " ".join(org.split()[1:]) if org else ""
                priv  = d.get("privacy", {})
                src["ipinfo"].update({
                    "ip":        d.get("ip", ip),
                    "city":      d.get("city", ""),
                    "region":    d.get("region", ""),
                    "country":   d.get("country", ""),
                    "org":       org,
                    "asn":       asn,
                    "isp":       isp,
                    "timezone":  d.get("timezone", ""),
                    "loc":       d.get("loc", ""),
                    "hostname":  d.get("hostname", ""),
                    "is_tor":    priv.get("tor",   False) if priv else False,
                    "is_proxy":  priv.get("proxy", False) if priv else False,
                    "is_vpn":    priv.get("vpn",   False) if priv else False,
                    "severity":  "HIGH" if priv.get("tor") else "LOW",
                })
    except Exception as e:
        src["ipinfo"]["error"] = str(e)
    return src


async def _shodan(ip: str) -> dict:
    src: dict[str, Any] = {"shodan": {"name": "Shodan"}}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"https://api.shodan.io/shodan/host/{ip}",
                params={"key": settings.SHODAN_API_KEY}
            )
            if r.status_code == 200:
                d     = r.json()
                ports = d.get("ports", [])
                vulns = list(d.get("vulns", {}).keys())
                banners = [
                    {"port": item.get("port"), "product": item.get("product", ""),
                     "version": item.get("version", "")}
                    for item in d.get("data", [])[:5]
                ]
                src["shodan"].update({
                    "open_ports":  ports,
                    "port_count":  len(ports),
                    "os":          d.get("os", "Unknown"),
                    "org":         d.get("org", ""),
                    "isp":         d.get("isp", ""),
                    "hostnames":   d.get("hostnames", [])[:3],
                    "country":     d.get("country_name", ""),
                    "vulns":       vulns,
                    "vuln_count":  len(vulns),
                    "banners":     banners,
                    "last_update": d.get("last_update", ""),
                    "severity":    "CRITICAL" if vulns else "HIGH" if len(ports) > 10 else "MEDIUM",
                })
            elif r.status_code == 404:
                src["shodan"]["note"] = "IP not indexed in Shodan"
            elif r.status_code == 401:
                src["shodan"]["note"] = "Invalid Shodan API key"
    except Exception as e:
        src["shodan"]["error"] = str(e)
    return src


async def _virustotal(ip: str) -> dict:
    src: dict[str, Any] = {"virustotal": {"name": "VirusTotal"}}
    if not settings.VIRUSTOTAL_API_KEY:
        src["virustotal"]["status"] = "skipped"
        src["virustotal"]["note"]   = "Add VIRUSTOTAL_API_KEY to .env for live results"
        # Demo data
        src["virustotal"]["malicious"]  = 0
        src["virustotal"]["suspicious"] = 0
        src["virustotal"]["harmless"]   = 70
        src["virustotal"]["severity"]   = "LOW"
        return src
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
                headers={"x-apikey": settings.VIRUSTOTAL_API_KEY}
            )
            if r.status_code == 200:
                attrs = r.json().get("data", {}).get("attributes", {})
                stats = attrs.get("last_analysis_stats", {})
                mal   = stats.get("malicious", 0)
                total = sum(stats.values()) or 1
                src["virustotal"].update({
                    "malicious":    mal,
                    "suspicious":   stats.get("suspicious", 0),
                    "harmless":     stats.get("harmless",   0),
                    "undetected":   stats.get("undetected", 0),
                    "total_engines":total,
                    "abuse_score":  round(mal / total * 100),
                    "reputation":   attrs.get("reputation", 0),
                    "country":      attrs.get("country", ""),
                    "asn":          attrs.get("asn", ""),
                    "as_owner":     attrs.get("as_owner", ""),
                    "severity":     "CRITICAL" if mal > 10 else "HIGH" if mal > 3 else "MEDIUM" if mal > 0 else "LOW",
                })
    except Exception as e:
        src["virustotal"]["error"] = str(e)
    return src


def _calc_risk(sources: dict) -> int:
    score = 0
    if "virustotal" in sources:
        score += min(sources["virustotal"].get("malicious", 0) * 5, 50)
        score += min(sources["virustotal"].get("abuse_score", 0) // 4, 20)
    if "shodan" in sources:
        score += min(sources["shodan"].get("vuln_count", 0) * 10, 30)
        score += min(sources["shodan"].get("port_count", 0) // 2, 10)
    if "ipinfo" in sources:
        if sources["ipinfo"].get("is_tor"):   score += 30
        if sources["ipinfo"].get("is_proxy"): score += 15
        if sources["ipinfo"].get("is_vpn"):   score += 10
    return min(score, 100)


def _build_summary(ip: str, sources: dict, risk: int) -> str:
    parts = [ip]
    if "ipinfo" in sources:
        i = sources["ipinfo"]
        loc = f"{i.get('city','')}, {i.get('country','')}".strip(", ")
        if loc: parts.append(loc)
        if i.get("isp"): parts.append(i["isp"])
    if "virustotal" in sources and sources["virustotal"].get("malicious", 0) > 0:
        parts.append(f"⚠ {sources['virustotal']['malicious']} engines flagged malicious")
    if "shodan" in sources and sources["shodan"].get("vuln_count", 0) > 0:
        parts.append(f"⚠ {sources['shodan']['vuln_count']} CVEs found")
    return " | ".join(filter(None, parts))
