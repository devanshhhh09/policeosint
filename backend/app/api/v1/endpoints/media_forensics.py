"""
Media Forensics Upload Endpoint
Accepts image upload, returns full forensics analysis
"""
import io
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from app.db.models.user import User
from app.api.deps import get_current_user, require_perm
from app.services.osint.media import investigate_media

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg","image/jpg","image/png","image/gif",
    "image/webp","image/bmp","image/tiff",
}
MAX_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_perm("investigate:run")),
):
    if file.content_type not in ALLOWED_TYPES:
        return JSONResponse(status_code=400, content={
            "error": f"Unsupported file type: {file.content_type}. Supported: JPEG, PNG, GIF, WEBP, BMP"
        })

    image_bytes = await file.read()

    if len(image_bytes) > MAX_SIZE:
        return JSONResponse(status_code=413, content={
            "error": "File too large. Maximum size is 20MB."
        })

    if len(image_bytes) < 100:
        return JSONResponse(status_code=400, content={
            "error": "File too small or empty."
        })

    result = await investigate_media(image_bytes, file.filename or "unknown")
    return result


import httpx, re
from urllib.parse import urlparse

ALLOWED_IMAGE_EXTENSIONS = {'.jpg','.jpeg','.png','.gif','.webp','.bmp','.tiff','.tif'}
ALLOWED_VIDEO_EXTENSIONS  = {'.mp4','.mov','.avi','.mkv','.webm','.m4v','.3gp'}

def _classify_url(url: str) -> str:
    path = urlparse(url).path.lower()
    ext  = '.' + path.rsplit('.',1)[-1] if '.' in path else ''
    if ext in ALLOWED_IMAGE_EXTENSIONS: return 'image'
    if ext in ALLOWED_VIDEO_EXTENSIONS: return 'video'
    return 'unknown'

def _extract_url_metadata(url: str, headers: dict, content_type: str,
                           content_length: str, final_url: str) -> dict:
    parsed   = urlparse(url)
    final_p  = urlparse(final_url)
    was_redirected = url.rstrip('/') != final_url.rstrip('/')
    ext      = parsed.path.rsplit('.',1)[-1].lower() if '.' in parsed.path else ''

    # Social platform detection
    domain   = parsed.netloc.lower()
    platform = 'Unknown'
    for p, keywords in {
        'WhatsApp':  ['whatsapp','wa.me','cdn.whatsapp'],
        'Instagram': ['instagram','cdninstagram','fbcdn'],
        'Twitter/X': ['twitter','twimg','pbs.twimg','t.co'],
        'Facebook':  ['facebook','fbcdn','fb.com'],
        'Telegram':  ['telegram','t.me','cdn.telegram'],
        'YouTube':   ['youtube','youtu.be','ytimg'],
        'TikTok':    ['tiktok','tiktokv'],
        'Reddit':    ['reddit','redd.it','redditmedia'],
        'Terabox':   ['terabox','1024terabox'],
        'Google':    ['googleusercontent','lh3.google','drive.google'],
        'Imgur':     ['imgur'],
        'Dropbox':   ['dropbox','dropboxusercontent'],
    }.items():
        if any(kw in domain for kw in keywords):
            platform = p
            break

    risk_flags = []
    if platform == 'Terabox':    risk_flags.append('⚠ Terabox link — commonly used for illegal content distribution')
    if was_redirected:           risk_flags.append(f'URL redirected to: {final_url[:80]}')
    if 'cdn' in domain:          risk_flags.append('Served from CDN — original upload source may differ')
    if platform in ('Unknown',): risk_flags.append('Unknown hosting platform')

    return {
        'original_url':   url,
        'final_url':      final_url,
        'was_redirected': was_redirected,
        'domain':         domain,
        'platform':       platform,
        'file_extension': ext,
        'content_type':   content_type,
        'content_length': content_length,
        'server':         headers.get('server',''),
        'last_modified':  headers.get('last-modified',''),
        'etag':           headers.get('etag',''),
        'cache_control':  headers.get('cache-control',''),
        'x_powered_by':  headers.get('x-powered-by',''),
        'risk_flags':     risk_flags,
        'all_headers':    {k:v for k,v in headers.items() if k.lower() not in
                           ('set-cookie','authorization','cookie')},
    }


@router.post("/analyze-url")
async def analyze_url(
    payload: dict,
    current_user: User = Depends(require_perm("investigate:run")),
):
    """
    Fetch a public image/video URL and analyze its metadata.
    Extracts HTTP headers, platform, redirect chain, and EXIF if image.
    """
    url = payload.get("url","").strip()
    if not url:
        return JSONResponse(status_code=400, content={"error": "URL required"})

    if not url.startswith(('http://','https://')):
        url = 'https://' + url

    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PoliceOSINT/1.0; Law Enforcement)"}
        ) as client:
            # HEAD request first for metadata
            try:
                head_resp = await client.head(url)
                final_url = str(head_resp.url)
                headers   = dict(head_resp.headers)
                ct        = head_resp.headers.get('content-type','')
                cl        = head_resp.headers.get('content-length','Unknown')
            except Exception:
                head_resp = None
                final_url = url
                headers   = {}
                ct        = ''
                cl        = 'Unknown'

            url_meta = _extract_url_metadata(url, headers, ct, cl, final_url)
            media_type = _classify_url(final_url) or _classify_url(url)

            # For images — download and do full EXIF analysis
            exif_result = None
            if media_type == 'image' or 'image' in ct:
                try:
                    get_resp    = await client.get(final_url)
                    image_bytes = get_resp.content
                    if len(image_bytes) > 0 and len(image_bytes) < 20*1024*1024:
                        filename    = final_url.split('/')[-1].split('?')[0] or 'image.jpg'
                        exif_result = await investigate_media(image_bytes, filename)
                        url_meta['content_length'] = f"{len(image_bytes)/1024:.1f} KB"
                except Exception as e:
                    exif_result = {"error": f"Could not download image for EXIF analysis: {str(e)[:100]}"}

            # For video — only header metadata
            video_meta = None
            if media_type == 'video' or 'video' in ct:
                video_meta = {
                    "note": "Video content — header metadata only. Full frame analysis not supported.",
                    "content_type":   ct,
                    "content_length": cl,
                    "platform":       url_meta['platform'],
                }

            return {
                "url":         url,
                "media_type":  media_type if media_type != 'unknown' else ('image' if 'image' in ct else 'video' if 'video' in ct else 'unknown'),
                "url_metadata":url_meta,
                "image_analysis": exif_result,
                "video_metadata": video_meta,
                "risk_score":  _url_risk_score(url_meta, exif_result),
                "summary":     _url_summary(url, url_meta, exif_result),
            }

    except httpx.TimeoutException:
        return JSONResponse(status_code=408, content={"error":"Request timed out — URL may be private or slow"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Failed to fetch URL: {str(e)[:200]}"})


def _url_risk_score(url_meta: dict, exif: dict | None) -> int:
    score = 0
    if 'Terabox' in url_meta.get('platform',''):     score += 40
    if url_meta.get('was_redirected'):                score += 10
    if exif and exif.get('gps_found'):                score += 25
    if exif and exif.get('manipulation',{}).get('is_likely_edited'): score += 15
    if url_meta.get('platform') == 'Unknown':         score += 10
    return min(score, 100)


def _url_summary(url: str, url_meta: dict, exif: dict | None) -> str:
    parts = [url_meta.get('platform','Unknown platform')]
    ct    = url_meta.get('content_type','')
    parts.append(ct.split(';')[0] if ct else 'Unknown type')
    if exif and exif.get('gps_found'):
        parts.append('GPS coordinates found')
    if exif and exif.get('device_info',{}).get('make'):
        parts.append(f"Shot on {exif['device_info']['make']}")
    if url_meta.get('risk_flags'):
        parts.append(f"{len(url_meta['risk_flags'])} risk flag(s)")
    return ' | '.join(parts)


import base64

@router.post("/reverse-search")
async def reverse_image_search(
    file: UploadFile = File(...),
    current_user: User = Depends(require_perm("investigate:run")),
):
    """
    Reverse image search using Google Vision API web detection.
    Finds pages, similar images, and matching images across the web.
    """
    from app.core.config import settings

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        return JSONResponse(status_code=413, content={"error": "Max 10MB"})

    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    api_key   = getattr(settings, 'GOOGLE_VISION_API_KEY', None)

    results = {
        "full_matches":    [],
        "partial_matches": [],
        "similar_images":  [],
        "pages_with_image":[],
        "best_guess_labels":[],
        "status":          "no_api_key",
        "manual_links":    _manual_search_links(),
    }

    if api_key:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://vision.googleapis.com/v1/images:annotate?key={api_key}",
                    json={"requests": [{
                        "image":    {"content": image_b64},
                        "features": [{"type": "WEB_DETECTION", "maxResults": 20}]
                    }]}
                )
                if resp.status_code == 200:
                    web = resp.json()['responses'][0].get('webDetection', {})
                    results.update({
                        "full_matches":    [{"url":m["url"],"score":m.get("score",0)} for m in web.get("fullMatchingImages",[])],
                        "partial_matches": [{"url":m["url"],"score":m.get("score",0)} for m in web.get("partialMatchingImages",[])],
                        "similar_images":  [{"url":m["url"],"score":m.get("score",0)} for m in web.get("visuallySimilarImages",[])],
                        "pages_with_image":[{"url":p["url"],"title":p.get("pageTitle","")} for p in web.get("pagesWithMatchingImages",[])],
                        "best_guess_labels":[l["label"] for l in web.get("bestGuessLabels",[])],
                        "status":          "success",
                        "total_found":     len(web.get("fullMatchingImages",[])) + len(web.get("pagesWithMatchingImages",[])),
                    })
                else:
                    results["status"] = f"api_error_{resp.status_code}"
                    results["error"]  = resp.json().get("error",{}).get("message","")
        except Exception as e:
            results["status"] = "error"
            results["error"]  = str(e)[:200]

    return results


def _manual_search_links() -> dict:
    return {
        "google":  "https://images.google.com/",
        "tineye":  "https://tineye.com/",
        "yandex":  "https://yandex.com/images/",
        "bing":    "https://www.bing.com/visualsearch",
        "note":    "Upload the image manually to these links for reverse search without API key",
    }
