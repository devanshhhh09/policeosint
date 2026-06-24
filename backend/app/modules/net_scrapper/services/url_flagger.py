"""
URL detection and risk flagging for monitored Telegram channels.
"""
import re
from datetime import datetime, timezone
from typing import List
import httpx
from app.core.config import settings

URL_PATTERN = re.compile(
    r'https?://[^\s<>"{}|\\^`\[\]]+|'
    r'(?:www\.)[^\s<>"{}|\\^`\[\]]+|'
    r'(?:t\.me|telegram\.me)/[^\s]+',
    re.IGNORECASE
)

SUSPICIOUS_URL_PATTERNS = {
    "file_sharing":    ["terabox", "mega.nz", "mediafire", "zippyshare",
                        "gofile", "4shared", "anonfiles"],
    "url_shortener":   ["bit.ly", "tinyurl", "t.co", "ow.ly",
                        "shorturl", "rb.gy", "cutt.ly", "is.gd"],
    "phishing_hints":  ["login", "verify", "secure", "account", "update",
                        "confirm", "kyc", "bank", "paytm", "upi"],
    "payment":         ["pay", "invest", "profit", "earn", "income",
                        "trading", "crypto", "bitcoin", "wallet"],
    "adult":           ["xxx", "nude", "leaked", "mms", "adult",
                        "18plus", "onlyfans", "cam"],
    "telegram_invite": ["t.me/joinchat", "t.me/+"],
}

# Risk weight per category
CATEGORY_RISK: dict[str, int] = {
    "file_sharing":    35,
    "url_shortener":   25,
    "phishing_hints":  40,
    "payment":         30,
    "adult":           50,   # high — may indicate CSAM distribution channels
    "telegram_invite": 20,
}

CATEGORY_LABEL: dict[str, str] = {
    "file_sharing":    "File sharing / data exfil link",
    "url_shortener":   "URL shortener — destination hidden",
    "phishing_hints":  "Phishing / credential harvest keywords",
    "payment":         "Suspicious payment / investment link",
    "adult":           "Adult / illicit content link",
    "telegram_invite": "Telegram group invite",
}

SUSPICIOUS_TLDS = {
    '.ru', '.cn', '.tk', '.ml', '.ga', '.cf', '.gq',
    '.xyz', '.top', '.work', '.click', '.loan',
}

def extract_urls(text: str) -> List[str]:
    return list(set(URL_PATTERN.findall(text)))

def _match_categories(url: str) -> list[dict]:
    """Return all pattern categories that match this URL."""
    url_lower = url.lower()
    hits = []
    for category, patterns in SUSPICIOUS_URL_PATTERNS.items():
        matched = [p for p in patterns if p in url_lower]
        if matched:
            hits.append({
                "category":    category,
                "label":       CATEGORY_LABEL[category],
                "matched_on":  matched,
                "risk_weight": CATEGORY_RISK[category],
            })
    return hits

def analyze_url(url: str) -> dict:
    from urllib.parse import urlparse
    try:
        parsed  = urlparse(url if url.startswith('http') else f'https://{url}')
        domain  = parsed.netloc.lower().replace('www.', '')
        path    = parsed.path.lower()
        tld     = '.' + domain.split('.')[-1] if '.' in domain else ''
        is_tg   = domain in ('t.me', 'telegram.me')
    except Exception:
        domain, path, tld, is_tg = url, '', '', False

    flags      = []
    risk_score = 0

    # ── Pattern-based detection ──────────────────────────────────────────
    category_hits = _match_categories(url)
    for hit in category_hits:
        flags.append(f"[{hit['category'].upper()}] {hit['label']} ({', '.join(hit['matched_on'])})")
        risk_score += hit['risk_weight']

    # ── Structural checks ────────────────────────────────────────────────
    if tld in SUSPICIOUS_TLDS:
        flags.append(f'Suspicious TLD ({tld})')
        risk_score += 30

    if not url.startswith('https'):
        flags.append('Non-HTTPS — insecure / unencrypted')
        risk_score += 10

    sub_count = domain.count('.')
    if sub_count >= 3:
        flags.append(f'Multiple subdomains ({sub_count}) — possible typosquat/phishing')
        risk_score += 20

    risk_score = min(risk_score, 100)

    # Determine primary category for badge color
    primary_category = category_hits[0]['category'] if category_hits else 'unknown'

    return {
        'url':              url,
        'domain':           domain,
        'tld':              tld,
        'is_telegram':      is_tg,
        'categories':       [h['category'] for h in category_hits],
        'category_details': category_hits,
        'primary_category': primary_category,
        'flags':            flags,
        'risk_score':       risk_score,
        'severity':         ('CRITICAL' if risk_score >= 70 else
                             'HIGH'     if risk_score >= 40 else
                             'MEDIUM'   if risk_score >= 20 else 'LOW'),
        'flagged':          risk_score >= 20 or bool(flags),
        'can_monitor':      True,
        'monitor_type':     'telegram' if is_tg else 'web',
        'detected_at':      datetime.now(timezone.utc).isoformat(),
    }

async def enrich_with_virustotal(url: str) -> dict:
    key = settings.VIRUSTOTAL_API_KEY
    if not key:
        return {'status': 'skipped', 'note': 'Add VIRUSTOTAL_API_KEY for live scan'}
    try:
        import base64
        url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip('=')
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f'https://www.virustotal.com/api/v3/urls/{url_id}',
                headers={'x-apikey': key}
            )
            if r.status_code == 200:
                stats = r.json().get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                mal   = stats.get('malicious', 0)
                return {
                    'status':     'scanned',
                    'malicious':  mal,
                    'suspicious': stats.get('suspicious', 0),
                    'harmless':   stats.get('harmless', 0),
                    'severity':   'CRITICAL' if mal > 5 else 'HIGH' if mal > 0 else 'CLEAN',
                }
    except Exception as e:
        return {'status': 'error', 'note': str(e)[:80]}
    return {'status': 'not_found'}

def process_message_for_urls(text: str, source_info: dict) -> dict:
    urls    = extract_urls(text)
    results = [analyze_url(u) for u in urls]
    flagged = [r for r in results if r['flagged']]
    return {
        'has_urls':        bool(urls),
        'url_count':       len(urls),
        'flagged_count':   len(flagged),
        'urls':            results,
        'flagged_urls':    flagged,
        'source':          source_info,
        'requires_action': any(r['risk_score'] >= 40 for r in results),
        'categories_found':list({c for r in flagged for c in r['categories']}),
    }
