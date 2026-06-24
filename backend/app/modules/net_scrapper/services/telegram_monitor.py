"""
Telegram Monitor Service
Uses Telethon for real-time channel/group monitoring.
Falls back to demo mode if TELEGRAM_API_ID not configured.
"""
import asyncio, re, logging
from datetime import datetime, timezone
from typing import Any
from app.core.config import settings
from app.modules.net_scrapper.services.content_analyzer import analyze_content

logger = logging.getLogger(__name__)

# Active monitors: source_id -> task
_active_monitors: dict[str, asyncio.Task] = {}
_client = None


def _has_telegram_creds() -> bool:
    api_id   = getattr(settings, "TELEGRAM_API_ID",   None)
    api_hash = getattr(settings, "TELEGRAM_API_HASH",  None)
    phone    = getattr(settings, "TELEGRAM_PHONE",     None)
    return bool(api_id and api_hash and phone)


async def get_client():
    """Get or create Telethon client."""
    global _client
    if not _has_telegram_creds():
        return None
    if _client and _client.is_connected():
        return _client
    try:
        from telethon import TelegramClient
        api_id   = int(getattr(settings, "TELEGRAM_API_ID",  0))
        api_hash = getattr(settings, "TELEGRAM_API_HASH", "")
        _client  = TelegramClient("policeosint_session", api_id, api_hash)
        await _client.start(phone=getattr(settings, "TELEGRAM_PHONE", ""))
        logger.info("Telegram client connected")
        return _client
    except Exception as e:
        logger.error("Telegram client error", exc_info=e)
        return None


async def get_channel_info(identifier: str) -> dict[str, Any]:
    """Get basic info about a Telegram channel/group."""
    client = await get_client()
    if not client:
        return _demo_channel_info(identifier)

    try:
        entity = await client.get_entity(identifier)
        return {
            "id":           entity.id,
            "title":        getattr(entity, "title",    identifier),
            "username":     getattr(entity, "username", ""),
            "participants": getattr(entity, "participants_count", 0),
            "is_group":     hasattr(entity, "megagroup") and entity.megagroup,
            "is_channel":   hasattr(entity, "broadcast") and entity.broadcast,
        }
    except Exception as e:
        logger.error("get_channel_info error", error=str(e))
        return _demo_channel_info(identifier)


async def scrape_recent_messages(identifier: str, limit: int = 50) -> list[dict]:
    """Scrape recent messages from a channel/group."""
    client = await get_client()
    if not client:
        return _demo_messages(identifier, limit)

    messages = []
    try:
        entity = await client.get_entity(identifier)
        async for msg in client.iter_messages(entity, limit=limit):
            if not msg.text:
                continue
            analysis = analyze_content(msg.text, "telegram")
            messages.append({
                "message_id":  str(msg.id),
                "text":        msg.text,
                "author":      str(msg.sender_id) if msg.sender_id else "unknown",
                "platform_ts": msg.date.replace(tzinfo=timezone.utc) if msg.date else datetime.now(timezone.utc),
                "analysis":    analysis,
                "has_media":   bool(msg.media),
            })
    except Exception as e:
        logger.error("scrape_messages error", error=str(e))
        return _demo_messages(identifier, limit)

    return messages


async def start_monitor(source_id: str, identifier: str, callback) -> bool:
    """Start real-time monitoring of a channel. callback(message_dict) called for each new message."""
    if source_id in _active_monitors:
        return True  # Already monitoring

    client = await get_client()
    if not client:
        logger.warning("Telegram not configured — monitor running in demo mode")
        task = asyncio.create_task(_demo_monitor(source_id, identifier, callback))
        _active_monitors[source_id] = task
        return True

    try:
        from telethon import events
        entity = await client.get_entity(identifier)

        @client.on(events.NewMessage(chats=entity))
        async def handler(event):
            text     = event.message.text or ""
            analysis = analyze_content(text, "telegram")
            await callback({
                "message_id":  str(event.message.id),
                "text":        text,
                "author":      str(event.message.sender_id or "unknown"),
                "platform_ts": event.message.date,
                "analysis":    analysis,
                "has_media":   bool(event.message.media),
            })

        task = asyncio.create_task(client.run_until_disconnected())
        _active_monitors[source_id] = task
        logger.info("Monitor started", source_id=source_id, channel=identifier)
        return True
    except Exception as e:
        logger.error("start_monitor error", error=str(e))
        return False


async def stop_monitor(source_id: str) -> bool:
    """Stop monitoring a channel."""
    task = _active_monitors.pop(source_id, None)
    if task:
        task.cancel()
        return True
    return False


def get_active_monitors() -> list[str]:
    return list(_active_monitors.keys())


# ── Demo mode (no Telegram credentials) ──────────────────────────────────────
DEMO_MESSAGES = [
    "🔥 EARN ₹5000/DAY FROM HOME! No experience needed. WhatsApp: +919876543210 Send ₹500 registration fee to kyc.verify@paytm",
    "INVESTMENT OPPORTUNITY! Double your money in 7 days. Min invest ₹10,000. Returns guaranteed. Contact @profit_guru_official",
    "Free videos 🔞 Click: https://terabox.com/s/fake123 Limited time only. Join now!",
    "Part time job available. Earn ₹15000/month. Data entry work. Pay: dailypay@ybl Training fee ₹200 only",
    "🚨 CRYPTO SIGNALS 100% accurate. BTC ETH BNB tips. Join paid group: @crypto_sure_shot Invest: 1A2b3C4d5E6f7G8h",
    "Leaked MMS viral 🔥 Download: https://terabox.com/s/leak456 Hurry before deleted!",
    "Work from home Amazon jobs. No target. ₹25000 salary. Call +918765432109. Registration: amazon.jobs@paytm",
    "Database dump available: 50L Indian Aadhar+Phone records. DM for price. @datadump_seller",
    "Hello everyone, today's weather is nice in Delhi!",
    "📢 Cryptocurrency investment returns 300% monthly. Initial: ₹50,000. Guaranteed profit. Wallet: 0x742d35Cc6634C",
]

def _demo_channel_info(identifier: str) -> dict:
    return {
        "id":           123456789,
        "title":        f"Demo Channel ({identifier})",
        "username":     identifier.replace("@","").replace("t.me/",""),
        "participants": 12847,
        "is_group":     True,
        "is_channel":   False,
        "demo":         True,
    }

def _demo_messages(identifier: str, limit: int) -> list[dict]:
    messages = []
    for i, text in enumerate(DEMO_MESSAGES[:limit]):
        analysis = analyze_content(text, "telegram")
        messages.append({
            "message_id":  str(1000 + i),
            "text":        text,
            "author":      f"user_{1000+i}",
            "platform_ts": datetime.now(timezone.utc),
            "analysis":    analysis,
            "has_media":   "terabox" in text.lower(),
            "demo":        True,
        })
    return messages

async def _demo_monitor(source_id: str, identifier: str, callback):
    """Simulate real-time messages in demo mode."""
    import random
    while True:
        await asyncio.sleep(random.uniform(15, 45))
        text     = random.choice(DEMO_MESSAGES)
        analysis = analyze_content(text, "telegram")
        try:
            await callback({
                "message_id":  str(random.randint(10000, 99999)),
                "text":        text,
                "author":      f"demo_user_{random.randint(100,999)}",
                "platform_ts": datetime.now(timezone.utc),
                "analysis":    analysis,
                "has_media":   "terabox" in text.lower(),
                "demo":        True,
            })
        except Exception:
            break
