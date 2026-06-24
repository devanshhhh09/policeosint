"""
Threat Intelligence Service — Phase 3
Sources: AlienVault OTX · VirusTotal · MITRE ATT&CK · Demo enrichment
"""
import asyncio, hashlib
from typing import Any
import httpx
from app.core.config import settings

# MITRE ATT&CK technique database (key techniques for Indian LEA)
MITRE_TECHNIQUES = {
    "T1566":     {"name": "Phishing",                    "tactic": "Initial Access",      "severity": "HIGH"},
    "T1566.001": {"name": "Spear-phishing Attachment",   "tactic": "Initial Access",      "severity": "HIGH"},
    "T1566.002": {"name": "Spear-phishing Link",         "tactic": "Initial Access",      "severity": "HIGH"},
    "T1486":     {"name": "Data Encrypted for Impact",   "tactic": "Impact",              "severity": "CRITICAL"},
    "T1059":     {"name": "Command & Scripting Interpreter","tactic":"Execution",          "severity": "HIGH"},
    "T1055":     {"name": "Process Injection",           "tactic": "Privilege Escalation","severity": "HIGH"},
    "T1078":     {"name": "Valid Accounts",              "tactic": "Persistence",         "severity": "MEDIUM"},
    "T1110":     {"name": "Brute Force",                 "tactic": "Credential Access",   "severity": "MEDIUM"},
    "T1190":     {"name": "Exploit Public-Facing App",   "tactic": "Initial Access",      "severity": "HIGH"},
    "T1071":     {"name": "App Layer Protocol (C2)",     "tactic": "Command & Control",   "severity": "HIGH"},
    "T1041":     {"name": "Exfiltration Over C2",        "tactic": "Exfiltration",        "severity": "HIGH"},
    "T1027":     {"name": "Obfuscated Files",            "tactic": "Defense Evasion",     "severity": "MEDIUM"},
    "T1083":     {"name": "File & Directory Discovery",  "tactic": "Discovery",           "severity": "LOW"},
    "T1082":     {"name": "System Info Discovery",       "tactic": "Discovery",           "severity": "LOW"},
    "T1105":     {"name": "Ingress Tool Transfer",       "tactic": "Command & Control",   "severity": "MEDIUM"},
    "T1133":     {"name": "External Remote Services",    "tactic": "Initial Access",      "severity": "HIGH"},
    "T1219":     {"name": "Remote Access Software",      "tactic": "Command & Control",   "severity": "HIGH"},
    "T1496":     {"name": "Resource Hijacking (Crypto)", "tactic": "Impact",              "severity": "MEDIUM"},
    "T1530":     {"name": "Data from Cloud Storage",     "tactic": "Collection",          "severity": "MEDIUM"},
    "T1588":     {"name": "Obtain Capabilities",         "tactic": "Resource Development","severity": "LOW"},
}

# Known threat actor groups targeting India
THREAT_ACTORS = {
    "SideCopy":    {"origin": "Pakistan", "targets": ["Indian Govt", "Defence", "IT"],
                    "ttps": ["T1566.001","T1059","T1027"], "active": True},
    "Transparent Tribe": {"origin": "Pakistan", "targets": ["Indian Military", "Govt"],
                    "ttps": ["T1566","T1105","T1219"], "active": True},
    "APT36":       {"origin": "Pakistan", "targets": ["Indian Defence", "Diplomatic"],
                    "ttps": ["T1566.001","T1055","T1041"], "active": True},
    "Lazarus Group":{"origin": "North Korea","targets": ["Banks", "Crypto Exchanges"],
                    "ttps": ["T1566","T1486","T1496"], "active": True},
    "FIN7":        {"origin": "Russia",   "targets": ["Financial Sector", "Retail"],
                    "ttps": ["T1566.001","T1059","T1078"], "active": True},
}

MALWARE_FAMILIES = {
    "CrimsonRAT":  {"type": "RAT",        "actor": "Transparent Tribe", "platform": "Windows"},
    "ObliqueRAT":  {"type": "RAT",        "actor": "Transparent Tribe", "platform": "Windows"},
    "LockBit":     {"type": "Ransomware", "actor": "LockBit Group",     "platform": "Windows/Linux"},
    "Conti":       {"type": "Ransomware", "actor": "Wizard Spider",     "platform": "Windows"},
    "Emotet":      {"type": "Loader",     "actor": "TA542",             "platform": "Windows"},
    "Cobalt Strike":{"type":"C2 Framework","actor": "Multiple",         "platform": "Windows/Linux"},
    "Mimikatz":    {"type": "Credential Dumper","actor": "Multiple",    "platform": "Windows"},
    "njRAT":       {"type": "RAT",        "actor": "Multiple",          "platform": "Windows"},
}


async def investigate_threat(ioc_type: str, query: str) -> dict[str, Any]:
    sources: dict[str, Any] = {}

    tasks = [
        _analyse_ioc(ioc_type, query),
        _otx_lookup(ioc_type, query),
        _virustotal_ioc(ioc_type, query),
        _mitre_mapping(query),
    ]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    for r in gathered:
        if isinstance(r, dict):
            sources.update(r)

    risk    = _calc_risk(sources)
    summary = _build_summary(ioc_type, query, sources, risk)
    return {
        "ioc_type":   ioc_type,
        "query":      query,
        "risk_score": risk,
        "sources":    sources,
        "summary":    summary,
    }


async def _analyse_ioc(ioc_type: str, query: str) -> dict:
    """Basic IOC analysis and classification."""
    import re
    src: dict[str, Any] = {"ioc_analysis": {"name": "IOC Analysis", "ioc": query, "type": ioc_type}}
    query_lower = query.lower()

    # Check against known malware families
    matched_malware = {k: v for k, v in MALWARE_FAMILIES.items()
                       if k.lower() in query_lower}

    # Check against threat actors
    matched_actors = {k: v for k, v in THREAT_ACTORS.items()
                      if k.lower() in query_lower}

    # Hash type detection
    hash_type = None
    if ioc_type == "hash":
        if re.match(r"^[a-fA-F0-9]{32}$", query):   hash_type = "MD5"
        elif re.match(r"^[a-fA-F0-9]{40}$", query): hash_type = "SHA1"
        elif re.match(r"^[a-fA-F0-9]{64}$", query): hash_type = "SHA256"

    src["ioc_analysis"].update({
        "classification":    ioc_type.upper(),
        "hash_type":         hash_type,
        "malware_matches":   matched_malware,
        "actor_matches":     matched_actors,
        "is_known_threat":   bool(matched_malware or matched_actors),
        "severity":          "CRITICAL" if matched_malware or matched_actors else "MEDIUM",
    })
    return src


async def _otx_lookup(ioc_type: str, query: str) -> dict:
    """AlienVault OTX threat intelligence lookup."""
    src: dict[str, Any] = {"otx": {"name": "AlienVault OTX"}}

    if not settings.OTX_API_KEY:
        # Rich demo data
        h = int(hashlib.md5(query.encode()).hexdigest(), 16)
        pulse_count = h % 8
        src["otx"].update({
            "status":       "demo",
            "note":         "⚠ Demo data — add OTX_API_KEY to .env (free at otx.alienvault.com)",
            "query":        query,
            "pulse_count":  pulse_count,
            "threat_score": min(pulse_count * 12, 95),
            "pulses": [
                {"name": f"Malicious Campaign #{i+1}", "tags": ["malware","phishing"],
                 "author": "OTX Community", "created": "2025-01-15"}
                for i in range(min(pulse_count, 3))
            ],
            "severity": "HIGH" if pulse_count >= 3 else "MEDIUM" if pulse_count >= 1 else "LOW",
            "demo": True,
        })
        return src

    endpoint_map = {
        "ip":     f"https://otx.alienvault.com/api/v1/indicators/IPv4/{query}/general",
        "domain": f"https://otx.alienvault.com/api/v1/indicators/domain/{query}/general",
        "hash":   f"https://otx.alienvault.com/api/v1/indicators/file/{query}/general",
        "url":    f"https://otx.alienvault.com/api/v1/indicators/url/{query}/general",
    }
    url = endpoint_map.get(ioc_type)
    if not url:
        src["otx"]["note"] = f"IOC type '{ioc_type}' not supported"
        return src

    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, headers={"X-OTX-API-KEY": settings.OTX_API_KEY})
            if r.status_code == 200:
                d = r.json()
                pulses = d.get("pulse_info", {}).get("pulses", [])
                src["otx"].update({
                    "pulse_count":  len(pulses),
                    "threat_score": min(len(pulses) * 12, 95),
                    "pulses": [{"name": p.get("name",""), "tags": p.get("tags",[])[:3]}
                               for p in pulses[:5]],
                    "country":      d.get("country_code",""),
                    "asn":          d.get("asn",""),
                    "severity":     "HIGH" if len(pulses) >= 3 else "MEDIUM" if pulses else "LOW",
                })
            else:
                src["otx"]["note"] = f"HTTP {r.status_code}"
    except Exception as e:
        src["otx"]["error"] = str(e)
    return src


async def _virustotal_ioc(ioc_type: str, query: str) -> dict:
    """VirusTotal IOC lookup."""
    src: dict[str, Any] = {"virustotal": {"name": "VirusTotal"}}

    if not settings.VIRUSTOTAL_API_KEY:
        h   = int(hashlib.md5(query.encode()).hexdigest(), 16)
        mal = (h % 15)
        src["virustotal"].update({
            "status":    "demo",
            "note":      "⚠ Demo data — add VIRUSTOTAL_API_KEY to .env (free)",
            "malicious": mal,
            "suspicious":h % 5,
            "harmless":  max(0, 70 - mal),
            "severity":  "CRITICAL" if mal > 10 else "HIGH" if mal > 5 else "MEDIUM" if mal > 0 else "LOW",
            "demo":      True,
        })
        return src

    endpoint_map = {
        "ip":     f"https://www.virustotal.com/api/v3/ip_addresses/{query}",
        "domain": f"https://www.virustotal.com/api/v3/domains/{query}",
        "hash":   f"https://www.virustotal.com/api/v3/files/{query}",
        "url":    f"https://www.virustotal.com/api/v3/urls/{query}",
    }
    url = endpoint_map.get(ioc_type)
    if not url:
        src["virustotal"]["note"] = f"IOC type '{ioc_type}' not supported"
        return src

    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, headers={"x-apikey": settings.VIRUSTOTAL_API_KEY})
            if r.status_code == 200:
                attrs = r.json().get("data", {}).get("attributes", {})
                stats = attrs.get("last_analysis_stats", {})
                mal   = stats.get("malicious", 0)
                src["virustotal"].update({
                    "malicious":    mal,
                    "suspicious":   stats.get("suspicious", 0),
                    "harmless":     stats.get("harmless",   0),
                    "total_engines":sum(stats.values()),
                    "reputation":   attrs.get("reputation", 0),
                    "severity":     "CRITICAL" if mal > 10 else "HIGH" if mal > 3 else "MEDIUM" if mal > 0 else "LOW",
                })
    except Exception as e:
        src["virustotal"]["error"] = str(e)
    return src


async def _mitre_mapping(query: str) -> dict:
    """Map IOC to MITRE ATT&CK techniques."""
    query_lower = query.lower()
    matched = []

    # Check if query contains technique IDs
    import re
    technique_ids = re.findall(r"T\d{4}(?:\.\d{3})?", query.upper())
    for tid in technique_ids:
        if tid in MITRE_TECHNIQUES:
            matched.append({"id": tid, **MITRE_TECHNIQUES[tid]})

    # Check malware → TTP mapping
    for malware, info in MALWARE_FAMILIES.items():
        if malware.lower() in query_lower:
            for ttp in info.get("ttps", []) if hasattr(info, "get") else []:
                if ttp in MITRE_TECHNIQUES and not any(m["id"] == ttp for m in matched):
                    matched.append({"id": ttp, **MITRE_TECHNIQUES[ttp]})

    # Default techniques if nothing matched
    if not matched and len(query) > 3:
        # Show relevant techniques based on IOC type
        defaults = ["T1566", "T1071", "T1041"]
        for tid in defaults:
            matched.append({"id": tid, **MITRE_TECHNIQUES[tid]})

    return {"mitre": {
        "name":        "MITRE ATT&CK Mapping",
        "techniques":  matched[:6],
        "count":       len(matched),
        "tactics":     list(set(m["tactic"] for m in matched)),
        "severity":    "HIGH" if matched else "LOW",
        "framework_url": "https://attack.mitre.org",
    }}


def _calc_risk(sources: dict) -> int:
    score = 0
    if "otx" in sources:
        score += min(sources["otx"].get("pulse_count", 0) * 10, 40)
    if "virustotal" in sources:
        score += min(sources["virustotal"].get("malicious", 0) * 4, 40)
    if "ioc_analysis" in sources:
        if sources["ioc_analysis"].get("is_known_threat"): score += 30
    return min(score, 100)


def _build_summary(ioc_type: str, query: str, sources: dict, risk: int) -> str:
    parts = [f"{ioc_type.upper()}: {query[:30]}"]
    if "otx" in sources and sources["otx"].get("pulse_count", 0) > 0:
        parts.append(f"OTX: {sources['otx']['pulse_count']} threat pulses")
    if "virustotal" in sources and sources["virustotal"].get("malicious", 0) > 0:
        parts.append(f"VT: {sources['virustotal']['malicious']} engines flagged")
    if "mitre" in sources:
        parts.append(f"MITRE: {sources['mitre']['count']} techniques mapped")
    return " | ".join(parts)
