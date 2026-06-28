"""
Telegram Member Profiler
Fetches members from groups, builds unified profiles, computes criticality.
Isolated add-on — does not modify any existing file.
"""
import re, asyncio, logging
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# ── Keyword lists for criticality scoring ─────────────────────────────────────
CRITICAL_KEYWORDS = [
    "guaranteed profit","guaranteed return","double your money","100% profit",
    "terabox","leaked mms","viral video","xxx","18+","adult content",
    "kyc expire","send otp","remote access","anydesk","teamviewer",
    "investment opportunity","risk free","earn daily","registration fee",
    "database dump","aadhar leak","pan card leak","combo list",
    "free premium","onlyfans leaked","private video",
]
SUSPICIOUS_KEYWORDS = [
    "work from home","part time job","earn from home","data entry job",
    "typing job","online job","crypto signal","forex trading",
    "binary trading","referral income","mlm","network marketing",
    "click here","join now","limited offer","hurry","free money",
    "loan approved","instant loan","no documents required",
]

# ── IOC regex ─────────────────────────────────────────────────────────────────
RE_PHONE  = re.compile(r'(?:\+91[\s\-]?)?[6-9]\d{9}\b')
RE_UPI    = re.compile(r'[a-zA-Z0-9.\-_+]+@(?:paytm|ybl|okaxis|okhdfcbank|oksbi|apl|upi|ibl|sbi|icici|hdfcbank|kotak)')
RE_BTC    = re.compile(r'\b(1|3|bc1)[A-Za-z0-9]{25,62}\b')
RE_ETH    = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
RE_URL    = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
RE_TERABOX= re.compile(r'https?://(?:www\.)?(?:terabox|1024terabox)\.(?:com|app)/[^\s]+')


def _extract_iocs(text: str) -> dict:
    t = text or ""
    return {
        "phones":   list(set(RE_PHONE.findall(t)))[:10],
        "upis":     list(set(RE_UPI.findall(t)))[:10],
        "wallets":  list(set(RE_BTC.findall(t) + RE_ETH.findall(t)))[:10],
        "links":    list(set(RE_URL.findall(t)))[:10],
        "terabox":  list(set(RE_TERABOX.findall(t)))[:5],
    }


def _score_message(text: str) -> tuple[float, bool]:
    """Return (risk_score 0-100, is_flagged)."""
    tl    = (text or "").lower()
    score = 0.0
    score += sum(15 for kw in CRITICAL_KEYWORDS    if kw in tl)
    score += sum(8  for kw in SUSPICIOUS_KEYWORDS  if kw in tl)
    iocs   = _extract_iocs(text)
    score += len(iocs["terabox"]) * 25
    score += len(iocs["upis"])    * 12
    score += len(iocs["wallets"]) * 15
    score += len(iocs["phones"])  * 8
    return min(score, 100.0), score >= 40


def _compute_criticality(risk_score: float, msg_count: int,
                          phones: list, upis: list, wallets: list) -> str:
    """Classify member into critical / suspicious / normal / unknown."""
    if msg_count == 0:
        return "unknown"
    if risk_score >= 60 or (upis and risk_score >= 30) or (wallets and risk_score >= 30):
        return "critical"
    if risk_score >= 25 or phones or upis:
        return "suspicious"
    return "normal"


# ── Database helpers ──────────────────────────────────────────────────────────
async def upsert_profile(
    db: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name:  str | None,
    phone:      str | None,
    channel_id: str,
) -> None:
    """Insert or update a member profile. Merges channel membership."""
    existing = await db.execute(
        text("SELECT id FROM telegram_profiles WHERE unique_telegram_id = :tid"),
        {"tid": telegram_id}
    )
    row = existing.fetchone()

    if row:
        await db.execute(text("""
            UPDATE telegram_profiles SET
                username    = COALESCE(:username,   username),
                first_name  = COALESCE(:first_name, first_name),
                last_name   = COALESCE(:last_name,  last_name),
                phone       = COALESCE(:phone,      phone),
                joined_channel_ids = ARRAY(
                    SELECT DISTINCT unnest(joined_channel_ids || ARRAY[:channel_id]::text[])
                ),
                last_updated = NOW()
            WHERE unique_telegram_id = :tid
        """), {
            "tid": telegram_id, "username": username,
            "first_name": first_name, "last_name": last_name,
            "phone": phone, "channel_id": channel_id,
        })
    else:
        await db.execute(text("""
            INSERT INTO telegram_profiles
                (unique_telegram_id, username, first_name, last_name,
                 phone, joined_channel_ids, criticality_flag)
            VALUES
                (:tid, :username, :first_name, :last_name,
                 :phone, ARRAY[:channel_id]::text[], 'unknown')
            ON CONFLICT (unique_telegram_id) DO NOTHING
        """), {
            "tid": telegram_id, "username": username,
            "first_name": first_name, "last_name": last_name,
            "phone": phone, "channel_id": channel_id,
        })


async def save_message(
    db: AsyncSession,
    telegram_id: int,
    channel_id: str,
    text_content: str,
    message_type: str = "text",
    platform_msg_id: str | None = None,
) -> None:
    """Save a member message and update their profile criticality."""
    iocs        = _extract_iocs(text_content)
    risk, flagged = _score_message(text_content)

    # Insert message
    await db.execute(text("""
        INSERT INTO telegram_member_messages
            (user_id, channel_id, message_text, message_type,
             extracted_links, extracted_upis, extracted_phones,
             extracted_wallets, risk_score, is_flagged, platform_msg_id)
        VALUES
            (:uid, :cid, :txt, :mtype,
             :links, :upis, :phones,
             :wallets, :risk, :flagged, :mid)
    """), {
        "uid":     telegram_id,
        "cid":     channel_id,
        "txt":     text_content,
        "mtype":   message_type,
        "links":   iocs["links"],
        "upis":    iocs["upis"],
        "phones":  iocs["phones"],
        "wallets": iocs["wallets"],
        "risk":    risk,
        "flagged": flagged,
        "mid":     platform_msg_id,
    })

    # Recompute member criticality from all their messages
    agg = await db.execute(text("""
        SELECT
            COUNT(*)::int          AS msg_count,
            COALESCE(MAX(risk_score), 0)   AS max_risk,
            ARRAY_AGG(DISTINCT p) FILTER (WHERE p IS NOT NULL) AS all_phones,
            ARRAY_AGG(DISTINCT u) FILTER (WHERE u IS NOT NULL) AS all_upis,
            ARRAY_AGG(DISTINCT w) FILTER (WHERE w IS NOT NULL) AS all_wallets
        FROM telegram_member_messages,
             LATERAL unnest(extracted_phones)  AS p,
             LATERAL unnest(extracted_upis)    AS u,
             LATERAL unnest(extracted_wallets) AS w
        WHERE user_id = :uid
    """), {"uid": telegram_id})
    row = agg.fetchone()
    if row:
        msg_count  = row[0] or 0
        max_risk   = row[1] or 0
        all_phones = row[2] or []
        all_upis   = row[3] or []
        all_wallets= row[4] or []
        flag       = _compute_criticality(max_risk, msg_count, all_phones, all_upis, all_wallets)
        await db.execute(text("""
            UPDATE telegram_profiles SET
                criticality_flag = :flag,
                risk_score       = :risk,
                message_count    = :cnt,
                last_active      = NOW(),
                extracted_phones = ARRAY(SELECT DISTINCT unnest(extracted_phones || :phones::text[])),
                extracted_upis   = ARRAY(SELECT DISTINCT unnest(extracted_upis   || :upis::text[])),
                extracted_wallets= ARRAY(SELECT DISTINCT unnest(extracted_wallets|| :wallets::text[])),
                last_updated     = NOW()
            WHERE unique_telegram_id = :uid
        """), {
            "flag": flag, "risk": max_risk, "cnt": msg_count,
            "phones": all_phones, "upis": all_upis,
            "wallets": all_wallets, "uid": telegram_id,
        })


async def fetch_channel_members(identifier: str, channel_id: str) -> dict[str, Any]:
    """
    Fetch all members from a Telegram group using Telethon.
    Falls back to demo data if credentials not configured.
    """
    from app.modules.net_scrapper.services.telegram_monitor import get_client
    client = await get_client()

    if not client:
        return _demo_members(identifier, channel_id)

    members = []
    try:
        from telethon.tl.functions.channels import GetParticipantsRequest
        from telethon.tl.types import ChannelParticipantsSearch

        entity = await client.get_entity(identifier)
        offset = 0
        limit  = 100

        while True:
            participants = await client(GetParticipantsRequest(
                channel=entity,
                filter=ChannelParticipantsSearch(""),
                offset=offset,
                limit=limit,
                hash=0,
            ))
            if not participants.users:
                break
            for user in participants.users:
                members.append({
                    "telegram_id": user.id,
                    "username":    user.username,
                    "first_name":  user.first_name,
                    "last_name":   user.last_name,
                    "phone":       getattr(user, "phone", None),
                    "is_bot":      user.bot,
                })
            offset += len(participants.users)
            if len(participants.users) < limit:
                break
            await asyncio.sleep(1)  # rate limit courtesy

        # Save all to DB
        async with AsyncSessionLocal() as db:
            for m in members:
                await upsert_profile(
                    db,
                    telegram_id=m["telegram_id"],
                    username=m["username"],
                    first_name=m["first_name"],
                    last_name=m["last_name"],
                    phone=m["phone"],
                    channel_id=channel_id,
                )
            await db.commit()

        return {
            "channel_id": channel_id,
            "total":      len(members),
            "members":    members,
            "status":     "fetched",
        }
    except Exception as e:
        logger.error("fetch_channel_members error", error=str(e))
        return _demo_members(identifier, channel_id)


def _demo_members(identifier: str, channel_id: str) -> dict:
    """Demo member profiles for when Telegram credentials are not configured."""
    import hashlib
    demo = []
    names = [
        (101, "scammer_raj",    "Raj",     "Kumar",  "+919876543210"),
        (102, "crypto_guru99",  "Priya",   "Sharma", None),
        (103, "earn_daily_now", "Vikram",  "Singh",  "+918765432109"),
        (104, "kyc_helpdesk",   "Support", "Team",   None),
        (105, "normal_user_1",  "Amit",    "Patel",  None),
        (106, "investor_club",  "Rahul",   "Verma",  "+917654321098"),
        (107, "terabox_share",  "Anon",    None,     None),
        (108, "regular_member", "Sunita",  "Devi",   None),
    ]
    for tid, uname, fname, lname, phone in names:
        demo.append({
            "telegram_id": tid,
            "username":    uname,
            "first_name":  fname,
            "last_name":   lname,
            "phone":       phone,
            "is_bot":      False,
            "demo":        True,
        })
    return {
        "channel_id": channel_id,
        "total":      len(demo),
        "members":    demo,
        "status":     "demo",
        "note":       "Add TELEGRAM_API_ID to .env for live member fetching",
    }
