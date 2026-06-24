"""
Identity Intelligence Service — Phase 2
Sources: HaveIBeenPwned · Hunter.io · Username enumeration · Phone lookup
Falls back to rich demo data when API keys not configured.
"""
import asyncio, re, hashlib
from typing import Any
import httpx
from app.core.config import settings

PLATFORMS = [
    {"name": "GitHub",    "url": "https://github.com/{}",                    "err": "Not Found"},
    {"name": "Reddit",    "url": "https://www.reddit.com/user/{}/about.json", "err": "404"},
    {"name": "Instagram", "url": "https://www.instagram.com/{}/",             "err": "Page Not Found"},
    {"name": "Twitter/X", "url": "https://twitter.com/{}",                   "err": "page doesn't exist"},
    {"name": "TikTok",    "url": "https://www.tiktok.com/@{}",               "err": "couldn't find"},
    {"name": "Pinterest", "url": "https://www.pinterest.com/{}/",            "err": "page not found"},
    {"name": "Telegram",  "url": "https://t.me/{}",                          "err": "If you have Telegram"},
    {"name": "LinkedIn",  "url": "https://www.linkedin.com/in/{}/",          "err": "Page not found"},
]

HEADERS    = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
DISPOSABLE = {"mailinator.com","guerrillamail.com","tempmail.com","throwaway.email",
               "yopmail.com","10minutemail.com","trashmail.com","fakeinbox.com","dispostable.com"}
FREE_MAIL  = {"gmail.com","yahoo.com","hotmail.com","outlook.com","protonmail.com","icloud.com","yahoo.co.in"}


async def investigate_identity(query_type: str, query: str) -> dict[str, Any]:
    sources: dict[str, Any] = {}

    if query_type == "email":
        results = await asyncio.gather(
            _hibp(query),
            _hunter(query),
            _email_analysis(query),
            return_exceptions=True
        )
    elif query_type == "username":
        results = await asyncio.gather(_username_enum(query), return_exceptions=True)
    elif query_type == "phone":
        results = await asyncio.gather(_phone_lookup(query), return_exceptions=True)
    elif query_type == "name":
        results = await asyncio.gather(_name_search(query), return_exceptions=True)
    else:
        results = await asyncio.gather(_email_analysis(query), return_exceptions=True)

    for r in results:
        if isinstance(r, dict):
            sources.update(r)

    risk    = _calc_risk(sources)
    summary = _build_summary(sources)
    return {
        "query_type": query_type,
        "query":      query,
        "risk_score": risk,
        "sources":    sources,
        "summary":    summary,
    }


# ── HaveIBeenPwned ────────────────────────────────────────────
async def _hibp(email: str) -> dict:
    src: dict[str, Any] = {"hibp": {"name": "HaveIBeenPwned"}}

    if not settings.HIBP_API_KEY:
        # Generate consistent demo data based on email hash
        h = int(hashlib.md5(email.encode()).hexdigest(), 16)
        breach_count = (h % 4)   # 0–3 breaches for demo
        all_breaches = [
            "Adobe (2023)", "LinkedIn (2021)", "RockYou2021",
            "Facebook (2019)", "Canva (2019)", "Zynga (2019)",
            "Dropbox (2012)", "Yahoo (2016)",
        ]
        breaches = all_breaches[:breach_count]
        src["hibp"].update({
            "status":       "demo",
            "note":         "⚠ Demo data — add HIBP_API_KEY to .env for real breach lookup",
            "api_key_url":  "https://haveibeenpwned.com/API/Key",
            "breach_count": breach_count,
            "breaches":     breaches,
            "severity":     "HIGH" if breach_count >= 2 else "MEDIUM" if breach_count == 1 else "LOW",
            "demo":         True,
        })
        return src

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
                headers={"hibp-api-key": settings.HIBP_API_KEY, "User-Agent": "PoliceOSINT/2.0"}
            )
            if r.status_code == 200:
                b = r.json()
                src["hibp"].update({
                    "breach_count": len(b),
                    "breaches":     [f"{x['Name']} ({x.get('BreachDate','')[:4]})" for x in b[:6]],
                    "severity":     "HIGH" if len(b) >= 3 else "MEDIUM" if len(b) >= 1 else "LOW",
                })
            elif r.status_code == 404:
                src["hibp"].update({"breach_count": 0, "breaches": [], "severity": "LOW",
                                    "note": "✓ No breaches found for this email"})
            elif r.status_code == 401:
                src["hibp"].update({"status": "error", "note": "Invalid HIBP API key"})
            else:
                src["hibp"].update({"status": "error", "note": f"HTTP {r.status_code}"})
    except Exception as e:
        src["hibp"]["error"] = str(e)
    return src


# ── Hunter.io ─────────────────────────────────────────────────
async def _hunter(email: str) -> dict:
    src: dict[str, Any] = {"hunter": {"name": "Hunter.io Email Verifier"}}

    if not settings.HUNTER_IO_API_KEY:
        # Demo data based on email
        parts  = email.split("@")
        domain = parts[1] if len(parts) == 2 else ""
        is_dis = domain in DISPOSABLE
        src["hunter"].update({
            "status":       "demo",
            "note":         "⚠ Demo data — add HUNTER_IO_API_KEY to .env for real verification",
            "api_key_url":  "https://hunter.io/api-keys",
            "email":        email,
            "domain":       domain,
            "disposable":   is_dis,
            "webmail":      domain in FREE_MAIL,
            "mx_records":   True,
            "smtp_valid":   not is_dis,
            "score":        10 if is_dis else 75,
            "severity":     "HIGH" if is_dis else "LOW",
            "demo":         True,
        })
        return src

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                "https://api.hunter.io/v2/email-verifier",
                params={"email": email, "api_key": settings.HUNTER_IO_API_KEY}
            )
            if r.status_code == 200:
                d = r.json().get("data", {})
                src["hunter"].update({
                    "status":     d.get("status", "unknown"),
                    "score":      d.get("score", 0),
                    "disposable": d.get("disposable", False),
                    "webmail":    d.get("webmail",    False),
                    "mx_records": d.get("mx_records", False),
                    "smtp_valid": d.get("smtp_server", False),
                    "severity":   "HIGH" if d.get("disposable") else "LOW",
                })
    except Exception as e:
        src["hunter"]["error"] = str(e)
    return src


# ── Email analysis (no API key needed) ────────────────────────
async def _email_analysis(email: str) -> dict:
    parts  = email.lower().split("@")
    domain = parts[1] if len(parts) == 2 else ""
    local  = parts[0]
    year   = re.search(r"(19|20)\d{2}", local)
    is_dis = domain in DISPOSABLE
    return {"email_analysis": {
        "name":          "Email Analysis",
        "email":         email,
        "domain":        domain,
        "local_part":    local,
        "is_disposable": is_dis,
        "is_free_provider": domain in FREE_MAIL,
        "possible_birth_year": year.group() if year else "Not detected",
        "has_numbers":   bool(re.search(r"\d", local)),
        "username_length": len(local),
        "risk_note":     "Disposable email — high fraud risk" if is_dis else
                         "Free email provider" if domain in FREE_MAIL else "Corporate/custom domain",
        "severity":      "HIGH" if is_dis else "LOW",
    }}


# ── Username enumeration ───────────────────────────────────────
async def _username_enum(username: str) -> dict:
    found, not_found = [], []

    async def _check(p: dict):
        url = p["url"].format(username)
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True, headers=HEADERS) as c:
                r = await c.get(url)
                exists = r.status_code == 200 and p["err"].lower() not in r.text.lower()
                entry  = {"platform": p["name"], "url": url, "found": exists}
                (found if exists else not_found).append(entry)
        except Exception:
            not_found.append({"platform": p["name"], "url": url, "found": False})

    await asyncio.gather(*[_check(p) for p in PLATFORMS])

    return {"username_enumeration": {
        "name":              "Username Enumeration",
        "username":          username,
        "platforms_checked": len(PLATFORMS),
        "found_count":       len(found),
        "not_found_count":   len(not_found),
        "found_on":          [x["platform"] for x in found],
        "not_found_on":      [x["platform"] for x in not_found],
        "profile_urls":      [x["url"] for x in found],
        "severity":          "HIGH" if len(found) >= 5 else "MEDIUM" if len(found) >= 2 else "LOW",
    }}


# ── Phone lookup ───────────────────────────────────────────────
async def _phone_lookup(phone: str) -> dict:
    src: dict[str, Any] = {"phone": {"name": "Phone Intelligence", "raw": phone}}
    try:
        import phonenumbers
        from phonenumbers import geocoder, carrier, timezone as tz
        parsed = phonenumbers.parse(phone, "IN")
        src["phone"].update({
            "valid":           phonenumbers.is_valid_number(parsed),
            "possible":        phonenumbers.is_possible_number(parsed),
            "e164_format":     phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
            "national_format": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
            "country_code":    parsed.country_code,
            "carrier":         carrier.name_for_number(parsed, "en") or "Unknown",
            "region":          geocoder.description_for_number(parsed, "en") or "Unknown",
            "timezones":       list(tz.time_zones_for_number(parsed)),
            "number_type":     str(phonenumbers.number_type(parsed)),
            "severity":        "MEDIUM",
        })
    except Exception as e:
        src["phone"]["error"] = str(e)
        src["phone"]["note"]  = "Try with country code e.g. +919876543210"
    return src


# ── Name search ────────────────────────────────────────────────
async def _name_search(name: str) -> dict:
    parts = name.strip().split()
    return {"name_search": {
        "name":        "Name Search",
        "query":       name,
        "name_parts":  parts,
        "first_name":  parts[0] if parts else "",
        "last_name":   parts[-1] if len(parts) > 1 else "",
        "search_links": {
            "Google":    f"https://www.google.com/search?q=%22{name.replace(' ','+')}%22",
            "LinkedIn":  f"https://www.linkedin.com/search/results/people/?keywords={name.replace(' ','%20')}",
            "Twitter/X": f"https://twitter.com/search?q=%22{name.replace(' ','+')}%22&f=user",
            "Facebook":  f"https://www.facebook.com/search/people?q={name.replace(' ','%20')}",
        },
        "tip":      "Use email or username query type for deeper results",
        "severity": "LOW",
    }}


# ── Risk + summary ─────────────────────────────────────────────
def _calc_risk(sources: dict) -> int:
    score = 0
    if "hibp" in sources:
        score += min(sources["hibp"].get("breach_count", 0) * 15, 45)
    if "email_analysis" in sources:
        if sources["email_analysis"].get("is_disposable"):    score += 25
    if "username_enumeration" in sources:
        score += min(sources["username_enumeration"].get("found_count", 0) * 5, 25)
    if "hunter" in sources:
        if sources["hunter"].get("disposable"):               score += 20
    return min(score, 100)


def _build_summary(sources: dict) -> str:
    parts = []
    if "hibp" in sources:
        bc = sources["hibp"].get("breach_count", 0)
        parts.append(f"{bc} breach(es) found" if bc > 0 else "No breaches found")
    if "email_analysis" in sources:
        if sources["email_analysis"].get("is_disposable"):
            parts.append("⚠ Disposable email")
        else:
            parts.append(f"Domain: {sources['email_analysis'].get('domain','')}")
    if "username_enumeration" in sources:
        fc = sources["username_enumeration"].get("found_count", 0)
        if fc > 0:
            plats = ", ".join(sources["username_enumeration"]["found_on"][:3])
            parts.append(f"Found on: {plats}")
    if "phone" in sources and sources["phone"].get("valid"):
        parts.append(f"{sources['phone'].get('carrier','')} · {sources['phone'].get('region','')}")
    return " | ".join(filter(None, parts)) or "Investigation complete"
