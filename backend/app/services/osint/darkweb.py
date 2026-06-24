"""
Dark Web Monitoring Service — Phase 3
Sources: Ahmia search · Credential leak detection · Demo breach alerts
"""
import asyncio, hashlib, re
from typing import Any
import httpx
from app.core.config import settings

# Simulated dark web threat categories
THREAT_CATEGORIES = {
    "credential_dump": "Credential dump — email/password combinations leaked",
    "card_dump":       "Credit/debit card data for sale",
    "data_breach":     "Organisational data breach listing",
    "ransomware":      "Ransomware group leak site",
    "fraud_service":   "Fraud-as-a-service offering",
    "malware_sale":    "Malware or exploit kit for sale",
}

KNOWN_LEAK_SITES = [
    "breachforums", "raidforums", "exposed.vc",
    "leakbase", "darkside", "lockbit",
]


async def monitor_dark_web(query_type: str, query: str) -> dict[str, Any]:
    sources: dict[str, Any] = {}

    tasks = [
        _credential_leak_check(query_type, query),
        _ahmia_search(query),
        _breach_intelligence(query_type, query),
    ]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    for r in gathered:
        if isinstance(r, dict):
            sources.update(r)

    risk    = _calc_risk(sources)
    summary = _build_summary(query_type, query, sources, risk)
    return {
        "query_type": query_type,
        "query":      query,
        "risk_score": risk,
        "sources":    sources,
        "summary":    summary,
    }


async def _credential_leak_check(query_type: str, query: str) -> dict:
    """Check for credential leaks — demo data without API key."""
    src: dict[str, Any] = {"credential_check": {"name": "Credential Leak Check"}}
    h = int(hashlib.md5(query.encode()).hexdigest(), 16)

    if query_type == "email":
        leak_count   = h % 5
        paste_count  = h % 8
        last_seen    = f"2024-{(h%12)+1:02d}-{(h%28)+1:02d}"
        sources_list = ["BreachForums", "Pastebin", "LeakBase", "ExposedVC", "RaidForums"]
        found_in     = sources_list[:(leak_count)]
        src["credential_check"].update({
            "email":       query,
            "leak_count":  leak_count,
            "paste_count": paste_count,
            "found_in":    found_in,
            "last_seen":   last_seen if leak_count > 0 else "Not found",
            "password_exposed": leak_count > 2,
            "plaintext_password": leak_count > 3,
            "severity":    "CRITICAL" if leak_count >= 3 else "HIGH" if leak_count >= 1 else "LOW",
            "note":        "Demo data — integrate DeHashed/LeakCheck API for live results",
        })

    elif query_type == "domain":
        employee_leaks = (h % 50) + 1
        src["credential_check"].update({
            "domain":         query,
            "employee_leaks": employee_leaks,
            "estimated_accounts": employee_leaks * 3,
            "threat_actors":  ["Unknown" if employee_leaks < 10 else "TA505"],
            "severity":       "CRITICAL" if employee_leaks > 20 else "HIGH" if employee_leaks > 5 else "MEDIUM",
            "note":           "Demo data — integrate DeHashed API for live org-level scanning",
        })

    elif query_type == "keyword":
        mention_count = h % 15
        src["credential_check"].update({
            "keyword":       query,
            "mention_count": mention_count,
            "forums_found":  KNOWN_LEAK_SITES[:mention_count % 4],
            "severity":      "HIGH" if mention_count > 5 else "MEDIUM" if mention_count > 0 else "LOW",
        })

    return src


async def _ahmia_search(query: str) -> dict:
    """Search Ahmia (Tor search engine accessible on clearnet)."""
    src: dict[str, Any] = {"ahmia": {"name": "Ahmia (Tor Search)"}}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://ahmia.fi/search/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code == 200:
                # Parse result count from response
                count_match = re.search(r"(\d+)\s+results?", r.text, re.IGNORECASE)
                onion_links = re.findall(r"[a-z2-7]{16,56}\.onion", r.text)
                result_count = int(count_match.group(1)) if count_match else len(onion_links)
                src["ahmia"].update({
                    "query":        query,
                    "result_count": result_count,
                    "onion_links":  list(set(onion_links))[:5],
                    "search_url":   f"https://ahmia.fi/search/?q={query}",
                    "severity":     "HIGH" if result_count > 10 else "MEDIUM" if result_count > 0 else "LOW",
                })
            else:
                src["ahmia"].update({
                    "note":     f"Ahmia returned HTTP {r.status_code}",
                    "severity": "LOW",
                })
    except Exception as e:
        src["ahmia"].update({
            "error":    str(e),
            "note":     "Ahmia unreachable — may be temporarily down",
            "severity": "LOW",
        })
    return src


async def _breach_intelligence(query_type: str, query: str) -> dict:
    """Breach intelligence summary."""
    h = int(hashlib.md5(query.encode()).hexdigest(), 16)
    recent_breaches = [
        {"name": "Indian Govt Portal", "date": "2024-11", "records": "2.1M", "type": "credential_dump"},
        {"name": "Telecom Provider",   "date": "2024-09", "records": "890K", "type": "data_breach"},
        {"name": "E-commerce Platform","date": "2024-07", "records": "4.5M", "type": "credential_dump"},
        {"name": "Banking App",        "date": "2024-05", "records": "156K", "type": "credential_dump"},
        {"name": "Healthcare Portal",  "date": "2024-03", "records": "320K", "type": "data_breach"},
    ]
    relevant = recent_breaches[:((h % 3) + 1)]
    return {"breach_intelligence": {
        "name":            "Breach Intelligence",
        "relevant_breaches": relevant,
        "total_records_exposed": sum(
            int(b["records"].replace("M","000000").replace("K","000")) for b in relevant
        ),
        "recommendations": [
            "Force password reset for affected accounts",
            "Enable 2FA on all accounts",
            "Monitor for fraudulent transactions",
            "Issue advisory to affected users",
        ],
        "severity": "HIGH" if len(relevant) >= 2 else "MEDIUM",
    }}


def _calc_risk(sources: dict) -> int:
    score = 0
    if "credential_check" in sources:
        lc = sources["credential_check"].get("leak_count", 0)
        el = sources["credential_check"].get("employee_leaks", 0)
        score += min((lc + el) * 10, 50)
    if "ahmia" in sources:
        score += min(sources["ahmia"].get("result_count", 0) * 3, 30)
    if "breach_intelligence" in sources:
        score += min(len(sources["breach_intelligence"].get("relevant_breaches", [])) * 10, 30)
    return min(score, 100)


def _build_summary(query_type: str, query: str, sources: dict, risk: int) -> str:
    parts = [query]
    if "credential_check" in sources:
        lc = sources["credential_check"].get("leak_count", 0)
        if lc > 0: parts.append(f"Found in {lc} leak(s)")
    if "ahmia" in sources and sources["ahmia"].get("result_count", 0) > 0:
        parts.append(f"{sources['ahmia']['result_count']} dark web mentions")
    return " | ".join(parts)
