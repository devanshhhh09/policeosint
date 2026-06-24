"""
Detects when a Telegram channel is redirecting its members to a new channel.
Scammers do this to evade takedowns — police need to follow the chain.
"""
import re
from datetime import datetime, timezone
from typing import Optional

# Patterns scammers use to redirect members
REDIRECT_PATTERNS = [
    # Direct t.me links
    re.compile(r'(?:https?://)?t\.me/([a-zA-Z0-9_+][a-zA-Z0-9_/+]*)', re.IGNORECASE),
    re.compile(r'(?:https?://)?telegram\.me/([a-zA-Z0-9_+][a-zA-Z0-9_/+]*)', re.IGNORECASE),

    # @username mentions
    re.compile(r'@([a-zA-Z][a-zA-Z0-9_]{3,})', re.IGNORECASE),
]

# Phrases that indicate the channel is being redirected/migrated
REDIRECT_PHRASES = [
    # English
    "join our new", "moved to", "we have moved", "new channel", "new group",
    "shifted to", "migrated to", "join now", "click to join", "link below",
    "new link", "backup channel", "alternative channel", "main channel",
    "old channel", "this channel will be deleted", "channel will be closed",
    "join before", "last message", "final message", "channel blocked",
    "account suspended", "new account",
    # Hindi/Hinglish common phrases
    "naya channel", "join karo", "new group join", "link join karo",
    "channel shift", "block ho gaya", "new link hai", "dusra channel",
]

PROMOTION_PHRASES = [
    "follow us on", "also join", "our other channel", "sister channel",
    "official channel", "main group", "vip group", "paid group",
    "premium group", "exclusive group",
]


def detect_channel_redirects(text: str) -> dict:
    """
    Analyze a message for channel redirect/migration signals.
    Returns detected channels and confidence score.
    """
    text_lower   = text.lower()
    found_links  = []
    found_users  = []

    # Extract all t.me links and @usernames
    for pattern in REDIRECT_PATTERNS:
        for match in pattern.finditer(text):
            val = match.group(1) if pattern.groups else match.group(0)
            if val.startswith('+') or '/' in val:
                # Invite link
                found_links.append({
                    'type':       'invite_link',
                    'value':      f't.me/{val}',
                    'raw':        match.group(0),
                    'is_private': val.startswith('+'),
                })
            else:
                found_users.append({
                    'type':  'username',
                    'value': val.lstrip('@'),
                    'raw':   match.group(0),
                })

    # Deduplicate
    seen = set()
    unique_links = []
    for item in found_links + found_users:
        key = item['value'].lower()
        if key not in seen:
            seen.add(key)
            unique_links.append(item)

    # Detect redirect intent
    redirect_phrases_found = [p for p in REDIRECT_PHRASES if p in text_lower]
    promo_phrases_found    = [p for p in PROMOTION_PHRASES if p in text_lower]

    is_redirect   = bool(redirect_phrases_found) and bool(unique_links)
    is_promotion  = bool(promo_phrases_found) and bool(unique_links)
    has_channels  = bool(unique_links)

    # Confidence scoring
    confidence = 0
    if redirect_phrases_found:  confidence += 50
    if promo_phrases_found:     confidence += 30
    if found_links:             confidence += 30   # invite links are stronger signal
    if found_users:             confidence += 15
    if 'block' in text_lower or 'suspend' in text_lower: confidence += 20
    if 'new' in text_lower and has_channels:             confidence += 10
    confidence = min(confidence, 100)

    intent = (
        'REDIRECT'  if is_redirect   else
        'PROMOTION' if is_promotion  else
        'MENTION'   if has_channels  else
        'NONE'
    )

    return {
        'has_channel_links':      has_channels,
        'is_redirect':            is_redirect,
        'is_promotion':           is_promotion,
        'intent':                 intent,
        'confidence':             confidence,
        'channels_found':         unique_links,
        'redirect_phrases':       redirect_phrases_found,
        'promotion_phrases':      promo_phrases_found,
        'invite_link_count':      len(found_links),
        'username_mention_count': len(found_users),
        'requires_action':        confidence >= 40 and has_channels,
        'detected_at':            datetime.now(timezone.utc).isoformat(),
    }


def build_redirect_alert(
    message_text: str,
    source_id: str,
    source_name: str,
    redirect_data: dict,
) -> Optional[dict]:
    """Build a structured alert for the officer if a redirect is detected."""
    if not redirect_data['requires_action']:
        return None

    severity = (
        'CRITICAL' if redirect_data['confidence'] >= 70 else
        'HIGH'     if redirect_data['confidence'] >= 50 else
        'MEDIUM'
    )

    return {
        'alert_type':    'channel_redirect',
        'severity':      severity,
        'source_id':     source_id,
        'source_name':   source_name,
        'message_text':  message_text[:300],
        'intent':        redirect_data['intent'],
        'confidence':    redirect_data['confidence'],
        'channels':      redirect_data['channels_found'],
        'redirect_phrases': redirect_data['redirect_phrases'],
        'detected_at':   redirect_data['detected_at'],
        'officer_action_required': True,
        'suggested_action': (
            'Channel is migrating — follow the chain and add new channel to monitoring'
            if redirect_data['is_redirect'] else
            'Channel promoting another group — may be expanding scam network'
        ),
    }
