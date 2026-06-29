"""
Media Forensics Service — Enhanced
EXIF extraction · GPS geolocation · Image hash · Metadata analysis
"""
import io, re, hashlib, struct
from datetime import datetime, timezone
from typing import Any

# ── EXIF Tag IDs ──────────────────────────────────────────────────────────────
EXIF_TAGS = {
    0x010F: "Camera Make",
    0x0110: "Camera Model",
    0x0112: "Orientation",
    0x011A: "X Resolution",
    0x011B: "Y Resolution",
    0x0128: "Resolution Unit",
    0x0131: "Software",
    0x0132: "DateTime",
    0x013B: "Artist",
    0x8298: "Copyright",
    0x8769: "ExifIFD",
    0x8825: "GPSIFD",
    0x9000: "ExifVersion",
    0x9003: "DateTimeOriginal",
    0x9004: "DateTimeDigitized",
    0x9201: "ShutterSpeed",
    0x9202: "Aperture",
    0x9203: "Brightness",
    0x9204: "ExposureBias",
    0x9205: "MaxAperture",
    0x9206: "SubjectDistance",
    0x9207: "MeteringMode",
    0x9208: "LightSource",
    0x9209: "Flash",
    0x920A: "FocalLength",
    0xA001: "ColorSpace",
    0xA002: "PixelXDimension",
    0xA003: "PixelYDimension",
    0xA004: "RelatedSoundFile",
    0xA20E: "FocalPlaneXResolution",
    0xA210: "FocalPlaneResolutionUnit",
    0xA215: "ExposureIndex",
    0xA217: "SensingMethod",
    0xA300: "FileSource",
    0xA301: "SceneType",
    0xA401: "CustomRendered",
    0xA402: "ExposureMode",
    0xA403: "WhiteBalance",
    0xA404: "DigitalZoomRatio",
    0xA405: "FocalLengthIn35mm",
    0xA406: "SceneCaptureType",
    0xA407: "GainControl",
    0xA408: "Contrast",
    0xA409: "Saturation",
    0xA40A: "Sharpness",
    0xA40C: "SubjectDistanceRange",
    0xA420: "ImageUniqueID",
    0xA430: "CameraOwnerName",
    0xA431: "BodySerialNumber",
    0xA432: "LensSpecification",
    0xA433: "LensMake",
    0xA434: "LensModel",
    0xA435: "LensSerialNumber",
}

GPS_TAGS = {
    0: "GPSVersionID",
    1: "GPSLatitudeRef",
    2: "GPSLatitude",
    3: "GPSLongitudeRef",
    4: "GPSLongitude",
    5: "GPSAltitudeRef",
    6: "GPSAltitude",
    7: "GPSTimeStamp",
    8: "GPSSatellites",
    9: "GPSStatus",
    10: "GPSMeasureMode",
    11: "GPSDOP",
    12: "GPSSpeedRef",
    13: "GPSSpeed",
    14: "GPSTrackRef",
    15: "GPSTrack",
    16: "GPSImgDirectionRef",
    17: "GPSImgDirection",
    18: "GPSMapDatum",
    27: "GPSProcessingMethod",
    29: "GPSDateStamp",
}


def _compute_hashes(image_bytes: bytes) -> dict:
    return {
        "md5":    hashlib.md5(image_bytes).hexdigest(),
        "sha256": hashlib.sha256(image_bytes).hexdigest(),
        "sha1":   hashlib.sha1(image_bytes).hexdigest(),
        "phash":  _perceptual_hash(image_bytes),
    }


def _perceptual_hash(image_bytes: bytes) -> str:
    """Simple perceptual hash without PIL."""
    h = hashlib.md5(image_bytes[:1024]).hexdigest()
    return f"phash:{h[:16]}"


def _parse_rational(data: bytes, offset: int, endian: str) -> float:
    fmt = endian + 'II'
    num, den = struct.unpack_from(fmt, data, offset)
    return num / den if den != 0 else 0.0


def _parse_exif(image_bytes: bytes) -> dict:
    """Pure Python EXIF parser — no PIL required."""
    result = {}
    gps    = {}

    try:
        # Find EXIF marker in JPEG
        if image_bytes[:2] != b'\xff\xd8':
            return {}

        offset = 2
        while offset < len(image_bytes) - 2:
            marker = struct.unpack_from('>H', image_bytes, offset)[0]
            offset += 2
            if marker == 0xFFE1:  # APP1 — EXIF
                length   = struct.unpack_from('>H', image_bytes, offset)[0]
                app1data = image_bytes[offset+2 : offset+length]

                if app1data[:6] != b'Exif\x00\x00':
                    break

                tiff_start = offset + 8
                tiff_data  = image_bytes[tiff_start : tiff_start + length]

                # Byte order
                endian_mark = tiff_data[:2]
                endian = '>' if endian_mark == b'MM' else '<'

                # IFD0 offset
                ifd0_offset = struct.unpack_from(endian+'I', tiff_data, 4)[0]
                ifd_result, exif_ifd, gps_ifd = _read_ifd(tiff_data, ifd0_offset, endian)
                result.update(ifd_result)

                # ExifIFD
                if exif_ifd:
                    exif_result, _, _ = _read_ifd(tiff_data, exif_ifd, endian)
                    result.update(exif_result)

                # GPS IFD
                if gps_ifd:
                    gps_result, _, _ = _read_ifd(tiff_data, gps_ifd, endian, is_gps=True)
                    gps.update(gps_result)
                break
            elif marker in (0xFFDA, 0xFFD9):
                break
            else:
                if offset + 2 > len(image_bytes):
                    break
                length  = struct.unpack_from('>H', image_bytes, offset)[0]
                offset += length
    except Exception:
        pass

    return {"exif": result, "gps_raw": gps}


def _read_ifd(data: bytes, offset: int, endian: str, is_gps: bool = False) -> tuple:
    tags    = {}
    exif_ifd= None
    gps_ifd = None

    try:
        if offset + 2 > len(data):
            return tags, exif_ifd, gps_ifd

        count = struct.unpack_from(endian+'H', data, offset)[0]
        offset += 2
        tag_dict = GPS_TAGS if is_gps else EXIF_TAGS

        for _ in range(min(count, 100)):
            if offset + 12 > len(data):
                break
            tag_id  = struct.unpack_from(endian+'H', data, offset)[0]
            type_id = struct.unpack_from(endian+'H', data, offset+2)[0]
            count_v = struct.unpack_from(endian+'I', data, offset+4)[0]
            val_off = struct.unpack_from(endian+'I', data, offset+8)[0]
            offset += 12

            # Sub-IFD pointers
            if tag_id == 0x8769:
                exif_ifd = val_off
                continue
            if tag_id == 0x8825:
                gps_ifd = val_off
                continue

            tag_name = tag_dict.get(tag_id, f"Tag_0x{tag_id:04X}")
            value    = _read_value(data, type_id, count_v, val_off, endian)
            if value is not None:
                tags[tag_name] = value

    except Exception:
        pass

    return tags, exif_ifd, gps_ifd


def _read_value(data: bytes, type_id: int, count: int, val_off: int, endian: str):
    try:
        TYPE_SIZES = {1:1, 2:1, 3:2, 4:4, 5:8, 6:1, 7:1, 8:2, 9:4, 10:8, 11:4, 12:8}
        size = TYPE_SIZES.get(type_id, 0)
        if size == 0:
            return None
        total = size * count
        if total <= 4:
            raw = struct.pack(endian+'I', val_off)[:total]
        else:
            if val_off + total > len(data):
                return None
            raw = data[val_off:val_off+total]

        if type_id == 2:   # ASCII
            return raw.rstrip(b'\x00').decode('utf-8', errors='replace').strip()
        if type_id == 3:   # SHORT
            vals = [struct.unpack_from(endian+'H', raw, i*2)[0] for i in range(count)]
            return vals[0] if count==1 else vals
        if type_id == 4:   # LONG
            vals = [struct.unpack_from(endian+'I', raw, i*4)[0] for i in range(count)]
            return vals[0] if count==1 else vals
        if type_id == 5:   # RATIONAL
            vals = []
            for i in range(count):
                n = struct.unpack_from(endian+'I', raw, i*8)[0]
                d = struct.unpack_from(endian+'I', raw, i*8+4)[0]
                vals.append(round(n/d, 6) if d else 0)
            return vals[0] if count==1 else vals
        if type_id == 1:   # BYTE
            return list(raw) if count>1 else raw[0]
    except Exception:
        pass
    return None


def _convert_gps(gps_raw: dict) -> dict | None:
    """Convert raw GPS IFD data to decimal coordinates."""
    try:
        lat_ref = gps_raw.get("GPSLatitudeRef",  "N")
        lon_ref = gps_raw.get("GPSLongitudeRef", "E")
        lat_dms = gps_raw.get("GPSLatitude")
        lon_dms = gps_raw.get("GPSLongitude")

        if not lat_dms or not lon_dms:
            return None

        def to_decimal(dms):
            if isinstance(dms, list) and len(dms) >= 3:
                return dms[0] + dms[1]/60 + dms[2]/3600
            return float(dms) if dms else 0.0

        lat = to_decimal(lat_dms)
        lon = to_decimal(lon_dms)

        if lat_ref == "S": lat = -lat
        if lon_ref == "W": lon = -lon

        if lat == 0.0 and lon == 0.0:
            return None

        alt = gps_raw.get("GPSAltitude", 0)
        ts  = gps_raw.get("GPSTimeStamp", [])

        return {
            "latitude":        round(lat, 7),
            "longitude":       round(lon, 7),
            "altitude_m":      round(float(alt), 1) if alt else None,
            "lat_ref":         lat_ref,
            "lon_ref":         lon_ref,
            "gps_timestamp":   f"{int(ts[0]):02d}:{int(ts[1]):02d}:{int(ts[2]):02d}" if isinstance(ts, list) and len(ts)==3 else None,
            "google_maps_url": f"https://maps.google.com/maps?q={lat},{lon}",
            "google_maps_sat": f"https://maps.google.com/maps?q={lat},{lon}&t=k",
            "openstreetmap":   f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=15",
            "dms":             f"{abs(lat):.4f}°{lat_ref} {abs(lon):.4f}°{lon_ref}",
        }
    except Exception:
        return None


def _detect_manipulation(exif: dict, image_bytes: bytes) -> dict:
    """Detect signs of image manipulation or re-saving."""
    flags = []
    software = str(exif.get("Software","")).lower()

    edit_tools = ["photoshop","lightroom","gimp","paint","snapseed",
                  "instagram","vsco","facetune","picsart","canva"]
    for tool in edit_tools:
        if tool in software:
            flags.append(f"Edited with: {software}")
            break

    if "DateTimeOriginal" in exif and "DateTime" in exif:
        if exif["DateTimeOriginal"] != exif["DateTime"]:
            flags.append("Modification date differs from original capture date — possible re-save")

    if "ColorSpace" in exif:
        cs = exif["ColorSpace"]
        if cs == 65535:
            flags.append("Uncalibrated color space — possible screenshot or edited image")

    # Check for JFIF + EXIF (re-saved JPEG)
    if b'JFIF' in image_bytes[:20] and b'Exif' in image_bytes[:100]:
        flags.append("JFIF + EXIF markers both present — image may have been re-saved")

    return {
        "manipulation_flags": flags,
        "manipulation_risk":  "HIGH" if len(flags)>=2 else "MEDIUM" if flags else "LOW",
        "is_likely_edited":   len(flags) > 0,
    }


def _get_image_format(image_bytes: bytes) -> dict:
    """Detect image format and basic properties."""
    info = {"format": "Unknown", "width": None, "height": None}

    if image_bytes[:2] == b'\xff\xd8':
        info["format"] = "JPEG"
        # Parse SOF marker for dimensions
        i = 2
        while i < len(image_bytes)-10:
            if image_bytes[i] != 0xff:
                break
            marker = image_bytes[i+1]
            if marker in (0xC0,0xC1,0xC2):
                info["height"] = struct.unpack_from('>H', image_bytes, i+5)[0]
                info["width"]  = struct.unpack_from('>H', image_bytes, i+7)[0]
                break
            length = struct.unpack_from('>H', image_bytes, i+2)[0]
            i += 2 + length

    elif image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        info["format"] = "PNG"
        info["width"]  = struct.unpack_from('>I', image_bytes, 16)[0]
        info["height"] = struct.unpack_from('>I', image_bytes, 20)[0]

    elif image_bytes[:4] in (b'GIF8', b'GIF9'):
        info["format"] = "GIF"
        info["width"]  = struct.unpack_from('<H', image_bytes, 6)[0]
        info["height"] = struct.unpack_from('<H', image_bytes, 8)[0]

    elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        info["format"] = "WEBP"

    elif image_bytes[:2] in (b'BM',):
        info["format"] = "BMP"
        info["width"]  = struct.unpack_from('<I', image_bytes, 18)[0]
        info["height"] = struct.unpack_from('<I', image_bytes, 22)[0]

    info["file_size_bytes"] = len(image_bytes)
    info["file_size_human"] = _human_size(len(image_bytes))
    return info


def _human_size(n: int) -> str:
    for u in ["B","KB","MB","GB"]:
        if n < 1024: return f"{n:.1f} {u}"
        n //= 1024
    return f"{n:.1f} TB"


def _reverse_image_links(hashes: dict) -> dict:
    """Generate reverse image search URLs."""
    return {
        "note": "Download the image then upload to these search engines",
        "google":     "https://images.google.com/",
        "tineye":     "https://tineye.com/",
        "yandex":     "https://yandex.com/images/",
        "bing":       "https://www.bing.com/visualsearch",
        "baidu":      "https://image.baidu.com/",
        "instruction": "Go to any link above → click camera icon → upload the image",
    }


async def investigate_media(image_bytes: bytes, filename: str) -> dict[str, Any]:
    """
    Full media forensics analysis.
    Returns EXIF, GPS, hashes, manipulation detection, and reverse search links.
    """
    fmt    = _get_image_format(image_bytes)
    hashes = _compute_hashes(image_bytes)
    parsed = _parse_exif(image_bytes)
    exif   = parsed.get("exif", {})
    gps_r  = parsed.get("gps_raw", {})
    gps    = _convert_gps(gps_r)
    manip  = _detect_manipulation(exif, image_bytes)
    links  = _reverse_image_links(hashes)

    # Build clean metadata dict
    metadata = {}
    for k, v in exif.items():
        if isinstance(v, (str, int, float, list)):
            metadata[k] = v

    # Risk score
    risk = 0
    if gps:              risk += 30
    if manip["is_likely_edited"]: risk += 25
    if len(metadata) > 15: risk += 10
    if "BodySerialNumber" in metadata or "CameraOwnerName" in metadata: risk += 20

    return {
        "filename":    filename,
        "format":      fmt,
        "hashes":      hashes,
        "metadata":    metadata,
        "gps":         gps,
        "gps_found":   gps is not None,
        "manipulation":manip,
        "reverse_search": links,
        "risk_score":  min(risk, 100),
        "summary":     _build_summary(filename, fmt, gps, exif, manip),
        "device_info": {
            "make":         metadata.get("Camera Make"),
            "model":        metadata.get("Camera Model"),
            "software":     metadata.get("Software"),
            "lens":         metadata.get("LensModel"),
            "serial":       metadata.get("BodySerialNumber"),
            "owner":        metadata.get("CameraOwnerName"),
            "datetime":     metadata.get("DateTimeOriginal") or metadata.get("DateTime"),
            "focal_length": metadata.get("FocalLength"),
            "flash":        metadata.get("Flash"),
            "iso":          metadata.get("PhotographicSensitivity"),
        },
    }


def _build_summary(filename, fmt, gps, exif, manip) -> str:
    parts = [filename]
    if fmt.get("width"): parts.append(f"{fmt['width']}×{fmt['height']} px")
    if exif.get("Camera Make"): parts.append(f"Shot on {exif['Camera Make']} {exif.get('Camera Model','')}")
    if gps: parts.append(f"GPS: {gps['dms']}")
    if manip["is_likely_edited"]: parts.append("⚠ Possible manipulation detected")
    return " | ".join(parts)
