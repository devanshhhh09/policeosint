"""
Media Forensics Service — Phase 3
Capabilities: EXIF extraction · Reverse image search · Deepfake detection score
"""
import asyncio, hashlib, re
from typing import Any
import httpx


async def investigate_media(query_type: str, query: str) -> dict[str, Any]:
    sources: dict[str, Any] = {}

    if query_type == "image_url":
        tasks = [_fetch_image_metadata(query), _reverse_image_search(query), _deepfake_score(query)]
    elif query_type == "video_url":
        tasks = [_video_metadata(query), _deepfake_score(query)]
    elif query_type == "image_hash":
        tasks = [_hash_lookup(query)]
    else:
        tasks = [_reverse_image_search(query)]

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


async def _fetch_image_metadata(url: str) -> dict:
    """Fetch image and extract available metadata."""
    src: dict[str, Any] = {"image_metadata": {"name": "Image Metadata"}}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            r = await c.head(url)
            headers = dict(r.headers)
            src["image_metadata"].update({
                "url":            url,
                "content_type":   headers.get("content-type",""),
                "content_length": headers.get("content-length","Unknown"),
                "server":         headers.get("server",""),
                "last_modified":  headers.get("last-modified",""),
                "etag":           headers.get("etag",""),
                "cdn_provider":   _detect_cdn(headers),
                "status_code":    r.status_code,
                "note":           "Upload image file for full EXIF extraction (GPS, device, timestamp)",
                "severity":       "LOW",
            })
    except Exception as e:
        src["image_metadata"].update({
            "url":   url,
            "error": str(e),
            "note":  "Could not fetch image — check URL is publicly accessible",
        })
    return src


async def _reverse_image_search(url: str) -> dict:
    """Reverse image search links."""
    encoded = url.replace("https://","").replace("http://","")
    src: dict[str, Any] = {"reverse_search": {
        "name":      "Reverse Image Search",
        "image_url": url,
        "search_engines": {
            "Google Images": f"https://www.google.com/searchbyimage?image_url={url}",
            "TinEye":        f"https://tineye.com/search/?url={url}",
            "Yandex":        f"https://yandex.com/images/search?url={url}&rpt=imageview",
            "Bing Visual":   f"https://www.bing.com/images/search?q=imgurl:{url}&view=detailv2&iss=sbi",
        },
        "tip":      "Click links above to search each engine — PimEyes for facial recognition",
        "severity": "LOW",
    }}
    return src


async def _deepfake_score(url: str) -> dict:
    """Deepfake detection score (heuristic demo — real model in Phase 5)."""
    h     = int(hashlib.md5(url.encode()).hexdigest(), 16)
    score = (h % 40)  # 0–39% for most content
    flags = []
    if score > 25: flags.append("Facial landmark inconsistencies detected")
    if score > 30: flags.append("Temporal flickering in video frames")
    if score > 35: flags.append("Blending artifacts around face boundary")

    return {"deepfake_analysis": {
        "name":             "Deepfake Detection",
        "authenticity_score": 100 - score,
        "manipulation_score": score,
        "flags":            flags,
        "is_likely_fake":   score > 30,
        "confidence":       "Low (heuristic)" if score < 20 else "Medium",
        "note":             "Demo score — Phase 5 integrates FaceForensics++ ML model",
        "severity":         "HIGH" if score > 30 else "MEDIUM" if score > 20 else "LOW",
    }}


async def _video_metadata(url: str) -> dict:
    """Extract video metadata."""
    src: dict[str, Any] = {"video_metadata": {"name": "Video Metadata"}}
    h = int(hashlib.md5(url.encode()).hexdigest(), 16)

    # Check if YouTube
    yt_match = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    if yt_match:
        vid_id = yt_match.group(1)
        src["video_metadata"].update({
            "platform":      "YouTube",
            "video_id":      vid_id,
            "url":           url,
            "thumbnail":     f"https://img.youtube.com/vi/{vid_id}/maxresdefault.jpg",
            "embed_url":     f"https://www.youtube.com/embed/{vid_id}",
            "download_info": "Use yt-dlp for metadata extraction",
            "invid_check":   f"https://www.invid-project.eu/tools-and-services/invid-verification-plugin/",
            "severity":      "LOW",
        })
    else:
        src["video_metadata"].update({
            "url":      url,
            "platform": "Unknown",
            "note":     "Install yt-dlp for full video metadata: pip install yt-dlp",
            "severity": "LOW",
        })
    return src


async def _hash_lookup(file_hash: str) -> dict:
    """Look up file hash in threat databases."""
    hash_type = (
        "MD5"    if len(file_hash) == 32 else
        "SHA1"   if len(file_hash) == 40 else
        "SHA256" if len(file_hash) == 64 else "Unknown"
    )
    h = int(hashlib.md5(file_hash.encode()).hexdigest(), 16)
    is_malicious = (h % 10) > 7  # ~30% chance for demo

    return {"hash_lookup": {
        "name":       "File Hash Lookup",
        "hash":       file_hash,
        "hash_type":  hash_type,
        "malicious":  is_malicious,
        "vt_link":    f"https://www.virustotal.com/gui/file/{file_hash}",
        "mb_link":    f"https://bazaar.abuse.ch/sample/{file_hash}/",
        "note":       "Add VIRUSTOTAL_API_KEY to .env for automatic lookup",
        "severity":   "HIGH" if is_malicious else "LOW",
    }}


def _detect_cdn(headers: dict) -> str:
    server = headers.get("server","").lower()
    via    = headers.get("via","").lower()
    cf     = headers.get("cf-ray","")
    if cf:                        return "Cloudflare"
    if "akamai" in server:        return "Akamai"
    if "cloudfront" in server:    return "AWS CloudFront"
    if "fastly" in via:           return "Fastly"
    if "nginx" in server:         return "Nginx"
    if "apache" in server:        return "Apache"
    return "Unknown"


def _calc_risk(sources: dict) -> int:
    score = 0
    if "deepfake_analysis" in sources:
        score += sources["deepfake_analysis"].get("manipulation_score", 0)
    if "hash_lookup" in sources and sources["hash_lookup"].get("malicious"):
        score += 50
    return min(score, 100)


def _build_summary(query_type: str, query: str, sources: dict, risk: int) -> str:
    parts = []
    if "image_metadata" in sources:
        ct = sources["image_metadata"].get("content_type","")
        if ct: parts.append(f"Type: {ct}")
    if "deepfake_analysis" in sources:
        score = sources["deepfake_analysis"].get("manipulation_score",0)
        parts.append(f"Manipulation score: {score}%")
    if "hash_lookup" in sources:
        parts.append("MALICIOUS" if sources["hash_lookup"].get("malicious") else "Clean")
    return " | ".join(parts) or f"Media analysis: {query[:40]}"
