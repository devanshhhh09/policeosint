"""
Domain & Website Investigation Service — Phase 2
Sources: python-whois · dnspython · SSL · VirusTotal · crt.sh
"""
import asyncio, re, ssl, socket
from datetime import datetime, timezone
from typing import Any
import httpx
from app.core.config import settings


def _clean(raw: str) -> str:
    raw = raw.strip().lower()
    return raw.replace("https://","").replace("http://","").split("/")[0].split("?")[0]


async def investigate_domain(domain: str) -> dict[str, Any]:
    clean = _clean(domain)
    tasks = [_whois(clean), _dns(clean), _ssl_check(clean), _virustotal(clean), _crtsh(clean)]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    sources: dict[str, Any] = {}
    for r in gathered:
        if isinstance(r, dict):
            sources.update(r)
    risk = _calc_risk(sources)
    return {"domain": clean, "query": domain,
            "risk_score": risk, "sources": sources,
            "summary": _build_summary(clean, sources, risk)}


async def _whois(domain: str) -> dict:
    src: dict[str, Any] = {"whois": {"name": "WHOIS"}}
    try:
        import whois as w
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, w.whois, domain)
        if data:
            created = data.get("creation_date")
            expires = data.get("expiration_date")
            if isinstance(created, list): created = created[0]
            if isinstance(expires, list): expires = expires[0]
            age_days = None
            if created:
                try:
                    if hasattr(created, "tzinfo") and created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    age_days = (datetime.now(timezone.utc) - created).days
                except Exception:
                    pass
            is_new = age_days is not None and age_days < 90
            src["whois"].update({
                "registrar":        str(data.get("registrar", "Unknown")),
                "creation_date":    str(created)[:10] if created else "Unknown",
                "expiration_date":  str(expires)[:10] if expires else "Unknown",
                "age_days":         age_days,
                "age_label":        f"{age_days} days" if age_days else "Unknown",
                "is_new_domain":    is_new,
                "privacy_protected":("redacted" in str(data).lower() or
                                     "privacy" in str(data.get("registrar","")).lower()),
                "nameservers":      list(data.get("name_servers", []))[:4],
                "emails":           list(set(data.get("emails", [])))[:3] if data.get("emails") else [],
                "severity":         "HIGH" if is_new else "LOW",
            })
    except Exception as e:
        src["whois"]["error"] = str(e)
        src["whois"]["note"]  = "WHOIS lookup failed — domain may not exist"
    return src


async def _dns(domain: str) -> dict:
    src: dict[str, Any] = {"dns": {"name": "DNS Records"}}
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5; resolver.lifetime = 5

        async def resolve(rtype: str) -> list:
            try:
                loop = asyncio.get_event_loop()
                ans  = await loop.run_in_executor(None, resolver.resolve, domain, rtype)
                return [r.to_text() for r in ans]
            except Exception:
                return []

        a, mx, ns, txt, aaaa = await asyncio.gather(
            resolve("A"), resolve("MX"), resolve("NS"), resolve("TXT"), resolve("AAAA")
        )
        spf   = next((t for t in txt if "v=spf"  in t.lower()), None)
        dmarc = next((t for t in txt if "v=dmarc" in t.lower()), None)
        src["dns"].update({
            "a_records":    a[:4],
            "aaaa_records": aaaa[:2],
            "mx_records":   [r.split()[-1] for r in mx][:3],
            "ns_records":   ns[:4],
            "txt_records":  txt[:3],
            "spf":          spf or "Not configured",
            "dmarc":        dmarc or "Not configured",
            "has_spf":      bool(spf),
            "has_dmarc":    bool(dmarc),
            "severity":     "MEDIUM" if not spf or not dmarc else "LOW",
        })
    except Exception as e:
        src["dns"]["error"] = str(e)
    return src


async def _ssl_check(domain: str) -> dict:
    src: dict[str, Any] = {"ssl": {"name": "SSL Certificate"}}
    try:
        loop = asyncio.get_event_loop()
        def _get_cert():
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
                s.settimeout(8)
                s.connect((domain, 443))
                return s.getpeercert()
        cert = await loop.run_in_executor(None, _get_cert)
        if cert:
            not_after  = datetime.strptime(cert["notAfter"],  "%b %d %H:%M:%S %Y %Z")
            not_before = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
            days_left  = (not_after - datetime.utcnow()).days
            issuer     = dict(x[0] for x in cert.get("issuer", []))
            subject    = dict(x[0] for x in cert.get("subject", []))
            sans       = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]
            lets_enc   = "Let's Encrypt" in issuer.get("organizationName", "")
            src["ssl"].update({
                "issuer":         issuer.get("organizationName", "Unknown"),
                "subject":        subject.get("commonName", domain),
                "valid_from":     str(not_before)[:10],
                "valid_until":    str(not_after)[:10],
                "days_remaining": days_left,
                "expired":        days_left < 0,
                "expiring_soon":  0 <= days_left <= 30,
                "san_domains":    sans[:6],
                "is_lets_encrypt":lets_enc,
                "wildcard":       any("*" in s for s in sans),
                "severity":       "HIGH" if days_left < 0 else "MEDIUM" if days_left <= 30 else "LOW",
            })
    except ssl.SSLError as e:
        src["ssl"].update({"error": str(e), "severity": "HIGH", "note": "SSL error"})
    except Exception as e:
        src["ssl"].update({"error": str(e), "note": "No HTTPS or connection failed"})
    return src


async def _virustotal(domain: str) -> dict:
    src: dict[str, Any] = {"virustotal": {"name": "VirusTotal"}}
    if not settings.VIRUSTOTAL_API_KEY:
        src["virustotal"]["status"] = "skipped"
        src["virustotal"]["note"]   = "Add VIRUSTOTAL_API_KEY to .env"
        return src
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"https://www.virustotal.com/api/v3/domains/{domain}",
                headers={"x-apikey": settings.VIRUSTOTAL_API_KEY}
            )
            if r.status_code == 200:
                attrs = r.json().get("data", {}).get("attributes", {})
                stats = attrs.get("last_analysis_stats", {})
                mal   = stats.get("malicious", 0)
                src["virustotal"].update({
                    "malicious":  mal,
                    "suspicious": stats.get("suspicious", 0),
                    "harmless":   stats.get("harmless",   0),
                    "reputation": attrs.get("reputation", 0),
                    "categories": list(attrs.get("categories", {}).values())[:4],
                    "severity":   "CRITICAL" if mal > 10 else "HIGH" if mal > 3 else "MEDIUM" if mal > 0 else "LOW",
                })
    except Exception as e:
        src["virustotal"]["error"] = str(e)
    return src


async def _crtsh(domain: str) -> dict:
    src: dict[str, Any] = {"subdomains": {"name": "Subdomain Discovery (crt.sh)"}}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://crt.sh/",
                params={"q": f"%.{domain}", "output": "json"},
                headers={"Accept": "application/json"}
            )
            if r.status_code == 200:
                data = r.json()
                subs = sorted(set(
                    entry.get("name_value","").lower()
                    for entry in data
                    if "*" not in entry.get("name_value","")
                ))[:25]
                src["subdomains"].update({
                    "count":      len(subs),
                    "subdomains": subs[:15],
                    "severity":   "MEDIUM" if len(subs) > 5 else "LOW",
                })
    except Exception as e:
        src["subdomains"]["error"] = str(e)
    return src


def _calc_risk(sources: dict) -> int:
    score = 0
    if "whois" in sources:
        if sources["whois"].get("is_new_domain"):      score += 30
        if sources["whois"].get("privacy_protected"):  score += 10
    if "virustotal" in sources:
        score += min(sources["virustotal"].get("malicious", 0) * 7, 40)
    if "ssl" in sources:
        if sources["ssl"].get("expired"):              score += 20
        if sources["ssl"].get("expiring_soon"):        score += 10
    return min(score, 100)


def _build_summary(domain: str, sources: dict, risk: int) -> str:
    parts = [domain]
    if "whois" in sources:
        age = sources["whois"].get("age_label","")
        reg = sources["whois"].get("registrar","")
        if age: parts.append(f"Age: {age}")
        if reg: parts.append(f"Reg: {reg}")
    if "virustotal" in sources and sources["virustotal"].get("malicious", 0) > 0:
        parts.append(f"⚠ Malicious: {sources['virustotal']['malicious']} engines")
    if "subdomains" in sources:
        parts.append(f"{sources['subdomains'].get('count',0)} subdomains found")
    return " | ".join(filter(None, parts))
