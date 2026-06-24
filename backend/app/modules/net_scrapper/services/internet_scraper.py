"""
Internet Scam Intelligence Scraper
Searches publicly available internet sources for scam content.
Uses: DuckDuckGo, RSS feeds, Reddit, public APIs — all legal passive OSINT.
"""
import asyncio, re, hashlib, logging
from datetime import datetime, timezone
from typing import Any
import httpx
from app.modules.net_scrapper.services.content_analyzer import analyze_content

logger = logging.getLogger(__name__)

# ── Search queries for each scam type ────────────────────────────────────────
SCAM_QUERIES = {
    "investment_scam": [
        "guaranteed profit investment India",
        "double money investment scheme India",
        "100% return investment telegram",
        "crypto investment guaranteed returns India",
        "trading signal group guaranteed profit",
        "forex trading guaranteed income India",
        "stock tips guaranteed profit telegram",
        "binary trading guaranteed returns",
    ],
    "fake_job": [
        "work from home earn 5000 daily India",
        "data entry job online payment daily",
        "earn money online Instagram job India",
        "part time job registration fee India",
        "Amazon work from home job India",
        "typing job earn daily payment",
        "online job no experience required India",
        "WhatsApp job opportunity earn daily",
    ],
    "upi_fraud": [
        "UPI fraud scam India 2024",
        "paytm scam alert India",
        "UPI collect request scam",
        "fake UPI payment screenshot scam",
        "KYC expire UPI scam India",
        "OTP fraud UPI India",
        "customer care UPI fraud",
        "QR code scan payment fraud India",
    ],
    "crypto_scam": [
        "crypto scam India telegram 2024",
        "bitcoin investment fraud India",
        "fake crypto exchange India",
        "crypto pump dump group India",
        "NFT scam India 2024",
        "crypto wallet drainer India",
        "fake crypto trading platform India",
        "DeFi scam India investment",
    ],
    "loan_scam": [
        "instant loan app fraud India",
        "fake loan app harassment India",
        "loan scam processing fee India",
        "digital lending fraud India",
        "loan recovery harassment India",
        "fake NBFC loan India scam",
        "WhatsApp loan offer scam India",
    ],
    "romance_scam": [
        "romance scam India online dating",
        "fake girlfriend investment fraud India",
        "matrimonial site fraud India",
        "online dating money scam India",
    ],
    "illegal_content": [
        "terabox link viral video India",
        "leaked video telegram channel",
        "MMS scam extortion India",
        "deepfake video scam India",
        "sextortion fraud India 2024",
    ],
}

# ── Risk keywords that boost score ────────────────────────────────────────────
HIGH_RISK_TERMS = [
    "guaranteed profit", "guaranteed return", "100% profit",
    "double your money", "risk free", "earn daily",
    "registration fee", "processing fee", "advance payment",
    "terabox", "leaked", "mms viral", "work from home earn",
    "invest now", "join now telegram", "limited offer",
    "UPI", "paytm", "crypto", "bitcoin",
]


async def search_duckduckgo(query: str, max_results: int = 10) -> list[dict]:
    """Search DuckDuckGo HTML (no API key needed, legal public search)."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            resp = await c.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query, "kl": "in-en"},
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; PoliceOSINT/1.0; Law Enforcement)",
                    "Accept-Language": "en-IN,en;q=0.9",
                }
            )
            if resp.status_code == 200:
                # Parse results from HTML
                text = resp.text
                # Extract result blocks
                result_pattern = re.finditer(
                    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?'
                    r'<a[^>]+class="result__url"[^>]*>([^<]+)</a>.*?'
                    r'<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>',
                    text, re.DOTALL
                )
                for i, match in enumerate(result_pattern):
                    if i >= max_results:
                        break
                    url     = match.group(1)
                    title   = re.sub(r'<[^>]+>', '', match.group(2)).strip()
                    domain  = match.group(3).strip()
                    snippet = re.sub(r'<[^>]+>', '', match.group(4)).strip()
                    results.append({"url": url, "title": title, "domain": domain, "snippet": snippet})

                # Fallback: simpler extraction
                if not results:
                    urls    = re.findall(r'href="(https?://[^"]+)"', text)
                    titles  = re.findall(r'<a[^>]+class="result__a"[^>]*>([^<]+)</a>', text)
                    snippets= re.findall(r'class="result__snippet"[^>]*>([^<]+)</a>', text)
                    for j in range(min(len(urls), len(titles), max_results)):
                        results.append({
                            "url":     urls[j],
                            "title":   re.sub(r'<[^>]+>','',titles[j]).strip(),
                            "domain":  re.sub(r'https?://([^/]+).*', r'\1', urls[j]),
                            "snippet": re.sub(r'<[^>]+>','',snippets[j]).strip() if j < len(snippets) else "",
                        })
    except Exception as e:
        logger.error("DuckDuckGo search error", query=query, error=str(e))
    return results


async def search_google_news_rss(query: str, max_results: int = 10) -> list[dict]:
    """Search Google News RSS — free, no API key, legal."""
    results = []
    try:
        encoded = query.replace(' ', '+')
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            resp = await c.get(
                f"https://news.google.com/rss/search?q={encoded}+India+scam&hl=en-IN&gl=IN&ceid=IN:en",
                headers={"User-Agent": "Mozilla/5.0 (compatible; PoliceOSINT/1.0)"}
            )
            if resp.status_code == 200:
                items = re.findall(
                    r'<item>(.*?)</item>', resp.text, re.DOTALL
                )
                for item in items[:max_results]:
                    title   = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item)
                    link    = re.search(r'<link>(.*?)</link>',  item)
                    desc    = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item)
                    pubdate = re.search(r'<pubDate>(.*?)</pubDate>', item)
                    if title and link:
                        results.append({
                            "url":        link.group(1).strip(),
                            "title":      title.group(1).strip(),
                            "domain":     "news.google.com",
                            "snippet":    re.sub(r'<[^>]+>', '', desc.group(1)).strip()[:200] if desc else "",
                            "published":  pubdate.group(1).strip() if pubdate else "",
                            "source_type":"news_rss",
                        })
    except Exception as e:
        logger.error("Google News RSS error", error=str(e))
    return results


async def search_reddit_public(query: str, max_results: int = 10) -> list[dict]:
    """Search Reddit public API — no auth needed for read-only."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            resp = await c.get(
                "https://www.reddit.com/search.json",
                params={"q": query, "sort": "new", "limit": max_results, "restrict_sr": False},
                headers={"User-Agent": "PoliceOSINT/1.0 (Law Enforcement OSINT Tool)"}
            )
            if resp.status_code == 200:
                posts = resp.json().get("data", {}).get("children", [])
                for post in posts:
                    d = post.get("data", {})
                    results.append({
                        "url":         f"https://reddit.com{d.get('permalink','')}",
                        "title":       d.get("title", ""),
                        "domain":      d.get("domain", "reddit.com"),
                        "snippet":     (d.get("selftext","") or d.get("url",""))[:200],
                        "author":      d.get("author",""),
                        "score":       d.get("score", 0),
                        "subreddit":   d.get("subreddit",""),
                        "source_type": "reddit",
                        "published":   datetime.fromtimestamp(
                            d.get("created_utc", 0), tz=timezone.utc
                        ).isoformat() if d.get("created_utc") else "",
                    })
    except Exception as e:
        logger.error("Reddit search error", error=str(e))
    return results


async def search_twitter_public(query: str, max_results: int = 10) -> list[dict]:
    """Search Twitter/X via nitter (public mirror, no API key needed)."""
    results = []
    nitter_instances = [
        "https://nitter.net",
        "https://nitter.privacydev.net",
        "https://nitter.poast.org",
    ]
    for instance in nitter_instances:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
                resp = await c.get(
                    f"{instance}/search",
                    params={"q": query, "f": "tweets"},
                    headers={"User-Agent": "Mozilla/5.0 (compatible; PoliceOSINT/1.0)"}
                )
                if resp.status_code == 200:
                    tweets = re.findall(
                        r'<div class="tweet-content[^"]*">(.*?)</div>', resp.text, re.DOTALL
                    )
                    authors = re.findall(
                        r'<a class="username"[^>]*>@([^<]+)</a>', resp.text
                    )
                    tweet_links = re.findall(
                        r'<a class="tweet-link"[^>]+href="([^"]+)"', resp.text
                    )
                    for j, tweet in enumerate(tweets[:max_results]):
                        clean   = re.sub(r'<[^>]+>', '', tweet).strip()
                        author  = authors[j] if j < len(authors) else "unknown"
                        t_link  = f"{instance}{tweet_links[j]}" if j < len(tweet_links) else ""
                        if clean:
                            results.append({
                                "url":         t_link,
                                "title":       clean[:100],
                                "domain":      "twitter.com",
                                "snippet":     clean[:300],
                                "author":      author,
                                "source_type": "twitter",
                            })
                    if results:
                        break
        except Exception:
            continue
    return results


async def fetch_cybercrime_alerts() -> list[dict]:
    """Fetch real cyber crime alerts from I4C/MHA RSS feeds."""
    results = []
    feeds = [
        "https://www.cybercrime.gov.in/rss/alerts",
        "https://cert-in.org.in/rss/advisories.rss",
    ]
    for feed_url in feeds:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                resp = await c.get(feed_url, headers={"User-Agent": "PoliceOSINT/1.0"})
                if resp.status_code == 200:
                    items = re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)
                    for item in items[:5]:
                        title = re.search(r'<title>(.*?)</title>', item)
                        link  = re.search(r'<link>(.*?)</link>', item)
                        if title and link:
                            results.append({
                                "url":         link.group(1),
                                "title":       re.sub(r'<[^>]+>','',title.group(1)),
                                "domain":      "cybercrime.gov.in",
                                "snippet":     "",
                                "source_type": "govt_alert",
                            })
        except Exception:
            pass
    return results


def enrich_result(result: dict, scam_type: str, query: str) -> dict:
    """Enrich a search result with analysis, risk score, and metadata."""
    combined_text = f"{result.get('title','')} {result.get('snippet','')}"
    analysis      = analyze_content(combined_text, "internet")

    # Override category with scam_type if analyzer didn't catch it
    if analysis["category"] == "normal" or analysis["category"] == "unclassified":
        from app.modules.net_scrapper.models import ContentCategory
        cat_map = {
            "investment_scam": ContentCategory.INVESTMENT_SCAM,
            "fake_job":        ContentCategory.FAKE_JOB,
            "upi_fraud":       ContentCategory.INVESTMENT_SCAM,
            "crypto_scam":     ContentCategory.CRYPTO_SCAM,
            "loan_scam":       ContentCategory.FAKE_JOB,
            "illegal_content": ContentCategory.ILLEGAL_CONTENT,
            "romance_scam":    ContentCategory.INVESTMENT_SCAM,
        }
        analysis["category"] = cat_map.get(scam_type, ContentCategory.UNCLASSIFIED)

    # Boost risk for high-risk terms
    text_lower = combined_text.lower()
    boost = sum(10 for term in HIGH_RISK_TERMS if term in text_lower)
    risk_score = min(analysis["risk_score"] + boost, 100)

    # Generate unique ID
    uid = hashlib.md5(result.get("url","").encode()).hexdigest()[:12]

    return {
        "id":           uid,
        "url":          result.get("url",""),
        "title":        result.get("title","")[:200],
        "domain":       result.get("domain",""),
        "snippet":      result.get("snippet","")[:500],
        "author":       result.get("author",""),
        "source_type":  result.get("source_type","web"),
        "scam_type":    scam_type,
        "search_query": query,
        "category":     str(analysis["category"]).replace("ContentCategory.",""),
        "risk_score":   risk_score,
        "is_flagged":   risk_score >= 40,
        "indicators":   analysis.get("indicators", []),
        "has_upi":      analysis.get("has_upi", False),
        "has_phone":    analysis.get("has_phone", False),
        "has_crypto":   analysis.get("has_crypto", False),
        "has_terabox":  analysis.get("has_terabox", False),
        "scraped_at":   datetime.now(timezone.utc).isoformat(),
        "published":    result.get("published",""),
    }


async def scrape_internet_for_scams(
    scam_types: list[str] | None = None,
    max_per_query: int = 5,
    include_reddit: bool = True,
    include_news: bool = True,
    include_twitter: bool = True,
) -> list[dict]:
    """
    Main scraper — searches internet for scam content across all types.
    Returns enriched results sorted by risk score.
    """
    if not scam_types:
        scam_types = list(SCAM_QUERIES.keys())

    all_results: list[dict] = []
    seen_urls: set[str]     = set()

    # Govt alerts first
    govt_alerts = await fetch_cybercrime_alerts()
    for alert in govt_alerts:
        enriched = enrich_result(alert, "govt_alert", "cybercrime alerts")
        enriched["risk_score"] = 80
        enriched["is_flagged"] = True
        all_results.append(enriched)

    # Search each scam type
    for scam_type in scam_types:
        queries = SCAM_QUERIES.get(scam_type, [])[:3]  # Max 3 queries per type

        for query in queries:
            tasks = []
            tasks.append(search_duckduckgo(query, max_per_query))
            if include_news:
                tasks.append(search_google_news_rss(query, max_per_query))
            if include_reddit:
                tasks.append(search_reddit_public(query + " scam India", max_per_query))
            if include_twitter:
                tasks.append(search_twitter_public(query, max_per_query // 2))

            gathered = await asyncio.gather(*tasks, return_exceptions=True)

            for batch in gathered:
                if isinstance(batch, list):
                    for result in batch:
                        url = result.get("url","")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            enriched = enrich_result(result, scam_type, query)
                            all_results.append(enriched)

            # Small delay to be respectful
            await asyncio.sleep(0.5)

    # Sort by risk score descending
    all_results.sort(key=lambda x: x["risk_score"], reverse=True)
    return all_results


async def scrape_url_for_scam(url: str) -> dict:
    """Scrape a specific URL and analyze it for scam content."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            resp = await c.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PoliceOSINT/1.0)"})
            if resp.status_code == 200:
                # Extract text
                text = re.sub(r'<script[^>]*>.*?</script>', '', resp.text, flags=re.DOTALL)
                text = re.sub(r'<style[^>]*>.*?</style>',  '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()[:5000]

                analysis = analyze_content(text, "web")
                return {
                    "url":        url,
                    "text":       text[:1000],
                    "category":   str(analysis["category"]),
                    "risk_score": analysis["risk_score"],
                    "is_flagged": analysis["is_flagged"],
                    "indicators": analysis["indicators"],
                    "status":     "success",
                }
    except Exception as e:
        return {"url": url, "error": str(e), "status": "failed"}
    return {"url": url, "status": "no_content"}
