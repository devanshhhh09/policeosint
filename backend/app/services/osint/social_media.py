"""
Social Media Intelligence Service — Phase 2
Username enumeration, profile analysis, cross-platform correlation
"""
import asyncio, re, hashlib
from typing import Any
import httpx

PLATFORMS = [
    {"name": "GitHub",      "url": "https://github.com/{}",                      "check": "404",             "category": "developer"},
    {"name": "Reddit",      "url": "https://www.reddit.com/user/{}/about.json",  "check": "404",             "category": "social"},
    {"name": "Instagram",   "url": "https://www.instagram.com/{}/",              "check": "Page Not Found",  "category": "social"},
    {"name": "Twitter/X",   "url": "https://twitter.com/{}",                     "check": "not found",       "category": "social"},
    {"name": "TikTok",      "url": "https://www.tiktok.com/@{}",                 "check": "couldn't find",   "category": "social"},
    {"name": "Pinterest",   "url": "https://www.pinterest.com/{}/",              "check": "not found",       "category": "social"},
    {"name": "Telegram",    "url": "https://t.me/{}",                            "check": "If you have",     "category": "messaging"},
    {"name": "LinkedIn",    "url": "https://www.linkedin.com/in/{}/",            "check": "not found",       "category": "professional"},
    {"name": "YouTube",     "url": "https://www.youtube.com/@{}",                "check": "404",             "category": "video"},
    {"name": "Snapchat",    "url": "https://www.snapchat.com/add/{}",            "check": "Sorry",           "category": "social"},
    {"name": "Quora",       "url": "https://www.quora.com/profile/{}",           "check": "404",             "category": "social"},
    {"name": "Medium",      "url": "https://medium.com/@{}",                     "check": "not found",       "category": "blog"},
    {"name": "Twitch",      "url": "https://www.twitch.tv/{}",                   "check": "404",             "category": "gaming"},
    {"name": "Steam",       "url": "https://steamcommunity.com/id/{}",           "check": "profile not found","category": "gaming"},
    {"name": "Pastebin",    "url": "https://pastebin.com/u/{}",                  "check": "Not Found",       "category": "data"},
    {"name": "Koo",         "url": "https://www.kooapp.com/profile/{}",          "check": "not found",       "category": "social"},
    {"name": "ShareChat",   "url": "https://sharechat.com/profile/{}",           "check": "not found",       "category": "social"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

# Scam-related username patterns
SCAM_PATTERNS = [
    r"invest",  r"profit",  r"earn",    r"forex",  r"crypto",
    r"bitcoin", r"trading", r"signal",  r"guru",   r"expert",
    r"kyc",     r"refund",  r"support", r"help",   r"official",
    r"care",    r"verify",  r"loan",    r"job",     r"work",
    r"money",   r"cash",    r"free",    r"prize",  r"winner",
]


async def _check_platform(
    session: httpx.AsyncClient,
    platform: dict,
    username: str,
) -> dict[str, Any]:
    url    = platform["url"].format(username)
    result = {
        "platform": platform["name"],
        "url":      url,
        "category": platform["category"],
        "found":    False,
        "status":   "not_found",
        "error":    None,
    }
    try:
        r = await session.get(url, headers=HEADERS, timeout=8, follow_redirects=True)
        body = r.text.lower()
        if r.status_code == 200 and platform["check"].lower() not in body:
            result["found"]  = True
            result["status"] = "found"
            # Extract profile snippets
            og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', r.text)
            og_desc  = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', r.text)
            followers= re.search(r'([\d,]+)\s*(?:followers|Followers)', r.text)
            if og_title:
                result["display_name"] = og_title.group(1)[:80]
            if og_desc:
                result["bio"] = og_desc.group(1)[:200]
            if followers:
                result["followers"] = followers.group(1)
        elif r.status_code == 404:
            result["status"] = "not_found"
        else:
            result["status"] = "unknown"
    except httpx.TimeoutException:
        result["status"] = "timeout"
        result["error"]  = "Request timed out"
    except Exception as e:
        result["status"] = "error"
        result["error"]  = str(e)[:100]
    return result


def _analyse_username(username: str) -> dict[str, Any]:
    """Analyse username for scam indicators and patterns."""
    u     = username.lower()
    flags = []

    # Check scam patterns
    matched_patterns = [p for p in SCAM_PATTERNS if re.search(p, u)]
    if matched_patterns:
        flags.append(f"Scam keywords in username: {', '.join(matched_patterns[:3])}")

    # Check numeric patterns
    if re.search(r'\d{4,}', u):
        flags.append("Contains long numeric sequence — possible auto-generated account")

    # Check impersonation patterns
    if re.search(r'official|verify|support|help|care', u):
        flags.append("Impersonation pattern — may be fake support/official account")

    # Check for known brand names
    brands = ["paytm","phonepe","gpay","amazon","flipkart","bank","sbi","hdfc","icici","rbi","npci"]
    matched_brands = [b for b in brands if b in u]
    if matched_brands:
        flags.append(f"Brand impersonation risk: {', '.join(matched_brands)}")

    # Risk score
    risk = min(len(flags) * 25 + len(matched_patterns) * 10, 100)

    return {
        "username":          username,
        "length":            len(username),
        "has_numbers":       bool(re.search(r'\d', username)),
        "has_special":       bool(re.search(r'[._\-]', username)),
        "scam_patterns":     matched_patterns,
        "brand_impersonation": matched_brands,
        "flags":             flags,
        "risk_score":        risk,
        "risk_label":        "HIGH" if risk >= 60 else "MEDIUM" if risk >= 30 else "LOW",
    }


async def investigate_social_media(username: str) -> dict[str, Any]:
    """
    Full social media OSINT for a username.
    Checks 17 platforms concurrently.
    """
    username  = username.strip().lstrip("@")
    analysis  = _analyse_username(username)

    # Check all platforms concurrently
    async with httpx.AsyncClient(timeout=10) as session:
        tasks   = [_check_platform(session, p, username) for p in PLATFORMS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    platform_results = []
    for r in results:
        if isinstance(r, dict):
            platform_results.append(r)

    found     = [r for r in platform_results if r["found"]]
    not_found = [r for r in platform_results if not r["found"]]

    # Cross-platform risk: same username on many platforms = coordinated actor
    if len(found) >= 8:
        analysis["flags"].append(f"High platform presence ({len(found)} platforms) — possible coordinated scam operation")
        analysis["risk_score"] = min(analysis["risk_score"] + 20, 100)

    # Build summary
    summary_parts = [f"Username @{username}"]
    summary_parts.append(f"Found on {len(found)}/{len(PLATFORMS)} platforms")
    if analysis["scam_patterns"]:
        summary_parts.append(f"Scam keywords: {', '.join(analysis['scam_patterns'][:2])}")

    return {
        "username":       username,
        "analysis":       analysis,
        "platforms": {
            "found":      found,
            "not_found":  not_found,
            "total_checked": len(platform_results),
            "found_count": len(found),
        },
        "risk_score":     analysis["risk_score"],
        "risk_label":     analysis["risk_label"],
        "flags":          analysis["flags"],
        "summary":        " | ".join(summary_parts),
        "sources_queried":[p["name"] for p in PLATFORMS],
    }


async def investigate_social_media_demo(username: str) -> dict[str, Any]:
    """
    Deterministic demo response for testing without live requests.
    """
    h     = int(hashlib.md5(username.lower().encode()).hexdigest(), 16)
    found = []
    not_found = []

    for i, p in enumerate(PLATFORMS):
        is_found = (h >> i) & 1
        r = {
            "platform": p["name"],
            "url":      p["url"].format(username),
            "category": p["category"],
            "found":    bool(is_found),
            "status":   "found" if is_found else "not_found",
        }
        if is_found:
            r["display_name"] = f"{username} | {p['name']}"
            r["followers"]    = str((h >> (i*2)) % 50000)
            r["bio"]          = f"Demo profile for {username} on {p['name']}"
            found.append(r)
        else:
            not_found.append(r)

    analysis = _analyse_username(username)
    return {
        "username":   username,
        "analysis":   analysis,
        "platforms": {
            "found":         found,
            "not_found":     not_found,
            "total_checked": len(PLATFORMS),
            "found_count":   len(found),
        },
        "risk_score":     analysis["risk_score"],
        "risk_label":     analysis["risk_label"],
        "flags":          analysis["flags"],
        "summary":        f"@{username} | Found on {len(found)}/{len(PLATFORMS)} platforms | Risk: {analysis['risk_score']}/100",
        "sources_queried":[p["name"] for p in PLATFORMS],
        "demo":           True,
    }
