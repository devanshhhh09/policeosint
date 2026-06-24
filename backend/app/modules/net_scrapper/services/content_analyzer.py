"""
Content Analyzer — Regex + AI categorization
Extracts IOCs and assigns risk scores to scraped content
"""
import re
from typing import Any
from app.modules.net_scrapper.models import ContentCategory, IndicatorType


# ── Regex patterns ─────────────────────────────────────────────────────────────
PATTERNS = {
    IndicatorType.PHONE_NUMBER: [
        r"\+91[\s\-]?\d{10}",
        r"0\d{10}",
        r"\b[6-9]\d{9}\b",
        r"\+\d{1,3}[\s\-]?\d{6,14}",
    ],
    IndicatorType.UPI_ID: [
        r"[a-zA-Z0-9.\-_+]+@(?:paytm|ybl|okaxis|okhdfcbank|okicici|oksbi|apl|upi|ibl|sbi|icici|hdfcbank|kotak)",
    ],
    IndicatorType.EMAIL: [
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    ],
    IndicatorType.CRYPTO_BTC: [
        r"\b(1|3|bc1)[A-Za-z0-9]{25,62}\b",
    ],
    IndicatorType.CRYPTO_ETH: [
        r"\b0x[a-fA-F0-9]{40}\b",
    ],
    IndicatorType.TERABOX_LINK: [
        r"https?://(?:www\.)?terabox\.com/[^\s]+",
        r"https?://(?:www\.)?terabox\.app/[^\s]+",
        r"https?://(?:www\.)?1024terabox\.com/[^\s]+",
    ],
    IndicatorType.FILE_LINK: [
        r"https?://(?:www\.)?mediafire\.com/[^\s]+",
        r"https?://mega\.nz/[^\s]+",
        r"https?://(?:www\.)?4shared\.com/[^\s]+",
        r"https?://(?:www\.)?zippyshare\.com/[^\s]+",
        r"https?://(?:www\.)?gofile\.io/[^\s]+",
    ],
    IndicatorType.URL: [
        r"https?://[^\s<>\"{}|\\^`\[\]]+",
    ],
    IndicatorType.USERNAME: [
        r"@[A-Za-z0-9_]{3,32}",
    ],
}

# ── Keyword sets for classification ───────────────────────────────────────────
FAKE_JOB_KEYWORDS = [
    "work from home","earn from home","part time job","data entry job",
    "typing job","online job","daily payment","₹500 per hour","₹1000 per day",
    "no experience required","earn 50000","freelance job","instagram job",
    "youtube job","amazon job","flipkart job","facebook job","whatsapp job",
    "packaging job","form filling","copy paste job","ad posting job",
    "daily income","instant payment","registration fee","joining fee",
    "training fee","registration charge","advance payment required",
]

INVESTMENT_SCAM_KEYWORDS = [
    "guaranteed profit","guaranteed return","double your money","triple investment",
    "100% profit","sure shot","risk free investment","binary trading",
    "forex trading","crypto investment","btc investment","eth investment",
    "invest 1000 get 5000","daily profit","weekly profit","monthly profit",
    "copy trading","signal group","pump and dump","pre-sale token",
    "ico investment","nft profit","defi profit","trading bot","auto trading",
    "referral income","mlm","network marketing","ponzi","pyramid scheme",
    "stock tips","intraday tips","option tips","sebi registered",
]

ILLEGAL_CONTENT_KEYWORDS = [
    "terabox","leaked","mms","viral video","hidden cam","bf video",
    "desi mms","college girl","school girl","nude","xxx","18+",
    "adult content","hot video","sexy video","private video leaked",
    "telegram adult","join for free videos","free premium","onlyfans leaked",
    "telegram link adult","link below","click for video",
]

LEAKED_DATA_KEYWORDS = [
    "aadhar leak","pan card leak","database leak","data dump","combo list",
    "email list","phone number list","credit card dump","cvv dump",
    "bank account details","kyc data","voter id leak","passport data",
    "login credentials","username password list","dark web dump",
]


def extract_indicators(text: str) -> list[dict]:
    """Extract all IOCs from text. Returns list of {type, value, context}."""
    if not text:
        return []

    found = []
    text_lower = text.lower()

    for ioc_type, pattern_list in PATTERNS.items():
        for pattern in pattern_list:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value   = match.group(0).strip()
                start   = max(0, match.start() - 50)
                end     = min(len(text), match.end() + 50)
                context = text[start:end].strip()

                # Skip very short URLs that are likely false positives
                if ioc_type == IndicatorType.URL and len(value) < 10:
                    continue

                # Deduplicate within same extraction
                if not any(f["value"] == value and f["type"] == ioc_type for f in found):
                    found.append({
                        "type":    ioc_type,
                        "value":   value,
                        "context": context,
                    })

    return found


def categorize_content(text: str) -> tuple[ContentCategory, float]:
    """
    Categorize content and assign risk score.
    Returns (category, risk_score 0-100).
    """
    if not text:
        return ContentCategory.NORMAL, 0.0

    text_lower = text.lower()
    scores: dict[str, int] = {
        "fake_job":        0,
        "investment_scam": 0,
        "illegal_content": 0,
        "leaked_data":     0,
    }

    # Count keyword hits
    for kw in FAKE_JOB_KEYWORDS:
        if kw in text_lower:
            scores["fake_job"] += 10

    for kw in INVESTMENT_SCAM_KEYWORDS:
        if kw in text_lower:
            scores["investment_scam"] += 10

    for kw in ILLEGAL_CONTENT_KEYWORDS:
        if kw in text_lower:
            scores["illegal_content"] += 15

    for kw in LEAKED_DATA_KEYWORDS:
        if kw in text_lower:
            scores["leaked_data"] += 12

    # Bonus for terabox/file links
    if re.search(r"terabox|mega\.nz|mediafire", text_lower):
        scores["illegal_content"] += 20

    # Bonus for UPI IDs with scam context
    if re.search(r"@paytm|@ybl|@okaxis", text_lower) and any(
        kw in text_lower for kw in ["send","transfer","pay","invest","profit"]
    ):
        scores["investment_scam"] += 15

    # Bonus for phone numbers in job context
    if re.search(r"\b[6-9]\d{9}\b", text) and any(
        kw in text_lower for kw in ["job","work","earn","income","salary"]
    ):
        scores["fake_job"] += 10

    # Determine winner
    max_cat = max(scores, key=lambda k: scores[k])
    max_score = scores[max_cat]

    if max_score == 0:
        return ContentCategory.NORMAL, 0.0

    # Map to category
    cat_map = {
        "fake_job":        ContentCategory.FAKE_JOB,
        "investment_scam": ContentCategory.INVESTMENT_SCAM,
        "illegal_content": ContentCategory.ILLEGAL_CONTENT,
        "leaked_data":     ContentCategory.LEAKED_DATA,
    }
    category   = cat_map[max_cat]
    risk_score = min(max_score, 100)

    return category, float(risk_score)


def score_indicator(indicator_type: IndicatorType, value: str, context: str = "") -> float:
    """Score an individual indicator."""
    base_scores = {
        IndicatorType.TERABOX_LINK:  85.0,
        IndicatorType.CRYPTO_BTC:    70.0,
        IndicatorType.CRYPTO_ETH:    70.0,
        IndicatorType.UPI_ID:        65.0,
        IndicatorType.PHONE_NUMBER:  50.0,
        IndicatorType.FILE_LINK:     60.0,
        IndicatorType.EMAIL:         30.0,
        IndicatorType.URL:           20.0,
        IndicatorType.USERNAME:      15.0,
    }
    score = base_scores.get(indicator_type, 10.0)

    # Context boost
    context_lower = (context or "").lower()
    if any(kw in context_lower for kw in ["scam","fraud","fake","illegal","leaked"]):
        score = min(score + 20, 100)
    if any(kw in context_lower for kw in ["invest","profit","earn","job","work from home"]):
        score = min(score + 15, 100)

    return score


def analyze_content(text: str, platform: str = "") -> dict[str, Any]:
    """Full analysis pipeline for a piece of scraped content."""
    category, risk_score = categorize_content(text)
    indicators           = extract_indicators(text)

    # Boost risk if multiple IOC types found
    if len(set(i["type"] for i in indicators)) >= 3:
        risk_score = min(risk_score + 15, 100)

    # Score each indicator
    for ind in indicators:
        ind["risk_score"] = score_indicator(ind["type"], ind["value"], ind.get("context",""))

    return {
        "category":   category,
        "risk_score": risk_score,
        "is_flagged": risk_score >= 40,
        "indicators": indicators,
        "indicator_count": len(indicators),
        "has_terabox":     any(i["type"] == IndicatorType.TERABOX_LINK for i in indicators),
        "has_upi":         any(i["type"] == IndicatorType.UPI_ID        for i in indicators),
        "has_crypto":      any(i["type"] in (IndicatorType.CRYPTO_BTC, IndicatorType.CRYPTO_ETH) for i in indicators),
        "has_phone":       any(i["type"] == IndicatorType.PHONE_NUMBER  for i in indicators),
    }
