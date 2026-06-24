"""
GEOINT Service — Phase 3
Capabilities: Photo geolocation · GPS extraction · Location verification · Sun angle
"""
import asyncio, re, math
from typing import Any
import httpx
from app.core.config import settings


async def investigate_geoint(query_type: str, query: str) -> dict[str, Any]:
    sources: dict[str, Any] = {}

    tasks = []
    if query_type == "coordinates":
        tasks = [_reverse_geocode(query), _location_intelligence(query)]
    elif query_type == "ip_location":
        tasks = [_ip_geolocation(query), _location_intelligence(query)]
    elif query_type == "address":
        tasks = [_forward_geocode(query)]
    elif query_type == "image_url":
        tasks = [_extract_image_location(query)]
    else:
        tasks = [_reverse_geocode(query)]

    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    for r in gathered:
        if isinstance(r, dict):
            sources.update(r)

    risk    = _calc_risk(sources)
    summary = _build_summary(query_type, query, sources)
    return {
        "query_type": query_type,
        "query":      query,
        "risk_score": risk,
        "sources":    sources,
        "summary":    summary,
    }


async def _reverse_geocode(coords: str) -> dict:
    """Reverse geocode coordinates to address."""
    src: dict[str, Any] = {"reverse_geocode": {"name": "Reverse Geocoding"}}
    try:
        # Parse coordinates
        parts = re.split(r"[,\s]+", coords.strip())
        if len(parts) >= 2:
            lat, lon = float(parts[0]), float(parts[1])
            src["reverse_geocode"]["latitude"]  = lat
            src["reverse_geocode"]["longitude"] = lon

            # Use Nominatim (free, no key needed)
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(
                    "https://nominatim.openstreetmap.org/reverse",
                    params={"lat": lat, "lon": lon, "format": "json"},
                    headers={"User-Agent": "PoliceOSINT/2.0 (law enforcement)"}
                )
                if r.status_code == 200:
                    d = r.json()
                    addr = d.get("address", {})
                    src["reverse_geocode"].update({
                        "formatted_address": d.get("display_name", ""),
                        "city":    addr.get("city") or addr.get("town") or addr.get("village",""),
                        "state":   addr.get("state", ""),
                        "country": addr.get("country", ""),
                        "country_code": addr.get("country_code","").upper(),
                        "postcode": addr.get("postcode",""),
                        "google_maps": f"https://maps.google.com/maps?q={lat},{lon}",
                        "osm_url":     f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=15",
                        "severity":    "LOW",
                    })
    except ValueError:
        src["reverse_geocode"]["error"] = "Invalid coordinates — use format: 28.6139, 77.2090"
    except Exception as e:
        src["reverse_geocode"]["error"] = str(e)
    return src


async def _forward_geocode(address: str) -> dict:
    """Forward geocode address to coordinates."""
    src: dict[str, Any] = {"geocode": {"name": "Address Geocoding"}}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 3},
                headers={"User-Agent": "PoliceOSINT/2.0"}
            )
            if r.status_code == 200:
                results = r.json()
                if results:
                    best = results[0]
                    lat, lon = float(best["lat"]), float(best["lon"])
                    src["geocode"].update({
                        "address":      address,
                        "latitude":     lat,
                        "longitude":    lon,
                        "display_name": best.get("display_name",""),
                        "type":         best.get("type",""),
                        "importance":   best.get("importance",0),
                        "google_maps":  f"https://maps.google.com/maps?q={lat},{lon}",
                        "alternatives": [r.get("display_name","") for r in results[1:3]],
                        "severity":     "LOW",
                    })
                else:
                    src["geocode"]["note"] = "Address not found"
    except Exception as e:
        src["geocode"]["error"] = str(e)
    return src


async def _ip_geolocation(ip: str) -> dict:
    """Geolocate an IP address."""
    src: dict[str, Any] = {"ip_location": {"name": "IP Geolocation"}}
    try:
        params = {"token": settings.IPINFO_TOKEN} if settings.IPINFO_TOKEN else {}
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://ipinfo.io/{ip}/json", params=params)
            if r.status_code == 200:
                d   = r.json()
                loc = d.get("loc", "").split(",")
                lat = float(loc[0]) if len(loc) == 2 else None
                lon = float(loc[1]) if len(loc) == 2 else None
                src["ip_location"].update({
                    "ip":         ip,
                    "latitude":   lat,
                    "longitude":  lon,
                    "city":       d.get("city",""),
                    "region":     d.get("region",""),
                    "country":    d.get("country",""),
                    "org":        d.get("org",""),
                    "timezone":   d.get("timezone",""),
                    "google_maps":f"https://maps.google.com/maps?q={lat},{lon}" if lat else "",
                    "accuracy":   "City-level (IP geolocation)",
                    "severity":   "LOW",
                })
    except Exception as e:
        src["ip_location"]["error"] = str(e)
    return src


async def _location_intelligence(coords: str) -> dict:
    """Generate location intelligence from coordinates."""
    src: dict[str, Any] = {"location_intel": {"name": "Location Intelligence"}}
    try:
        parts = re.split(r"[,\s]+", coords.strip())
        if len(parts) >= 2:
            lat, lon = float(parts[0]), float(parts[1])

            # Determine if in India
            in_india = (8.0 <= lat <= 37.0) and (68.0 <= lon <= 97.0)

            # Sun position calculation (simplified)
            import datetime
            now   = datetime.datetime.utcnow()
            hour  = now.hour + lon / 15
            is_day = 6 <= hour % 24 <= 18

            src["location_intel"].update({
                "latitude":      lat,
                "longitude":     lon,
                "in_india":      in_india,
                "hemisphere":    "Northern" if lat > 0 else "Southern",
                "is_daytime":    is_day,
                "utc_offset":    f"UTC+{lon/15:+.1f}",
                "street_view":   f"https://www.google.com/maps/@{lat},{lon},3a,75y,90t/data=!3m1!1e3",
                "satellite":     f"https://maps.google.com/maps?q={lat},{lon}&t=k",
                "nearby_search": f"https://www.google.com/maps/search/police+station/@{lat},{lon},14z",
                "severity":      "LOW",
            })
    except Exception as e:
        src["location_intel"]["error"] = str(e)
    return src


async def _extract_image_location(image_url: str) -> dict:
    """Attempt to extract location from image URL (EXIF in Phase 3 media service)."""
    src: dict[str, Any] = {"image_location": {"name": "Image Location Extraction"}}
    src["image_location"].update({
        "image_url":  image_url,
        "note":       "Upload image file for full EXIF GPS extraction",
        "tip":        "Use Media Forensics module to extract GPS from uploaded images",
        "severity":   "LOW",
    })
    return src


def _calc_risk(sources: dict) -> int:
    return 0  # GEOINT is informational, not risk-based


def _build_summary(query_type: str, query: str, sources: dict) -> str:
    parts = []
    if "reverse_geocode" in sources:
        city    = sources["reverse_geocode"].get("city","")
        country = sources["reverse_geocode"].get("country","")
        if city or country: parts.append(f"{city}, {country}".strip(", "))
    if "geocode" in sources:
        lat = sources["geocode"].get("latitude","")
        lon = sources["geocode"].get("longitude","")
        if lat: parts.append(f"Coords: {lat}, {lon}")
    if "ip_location" in sources:
        city    = sources["ip_location"].get("city","")
        country = sources["ip_location"].get("country","")
        org     = sources["ip_location"].get("org","")
        parts.append(f"{city}, {country} · {org}".strip(" ·"))
    return " | ".join(filter(None, parts)) or f"GEOINT: {query}"
