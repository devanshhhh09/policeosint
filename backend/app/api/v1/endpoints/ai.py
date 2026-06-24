from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.core.config import settings
from app.db.models.user import User
from app.api.deps import get_current_user
import httpx, structlog, os

router = APIRouter()
logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are PoliceOSINT AI Copilot — expert assistant for Indian cyber crime investigation.
Help officers with:
- FIR support notes with correct IPC sections (419, 420, 66C, 66D, 66F IT Act)
- Digital evidence correlation and preservation
- MITRE ATT&CK technique explanations
- UPI fraud investigation steps
- Suspect profiling guidance
- Crypto tracing methodology
Be precise, professional, and reference Indian cyber laws accurately."""

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[dict] = None

class ChatResponse(BaseModel):
    message: str
    model_used: str

FALLBACKS = {
    "fir":    """FIR Support — Cyber Crime\n\nApplicable Sections:\n• Section 419 IPC — Cheating by personation\n• Section 420 IPC — Cheating (financial fraud)\n• Section 66C IT Act — Identity theft\n• Section 66D IT Act — Cheating via computer resource\n• Section 66F IT Act — Cyber terrorism (if applicable)\n\nRecommended Actions:\n1. Freeze suspect UPI ID via PSP u/s 91 CrPC\n2. Request transaction logs from bank\n3. Collect CDR from telecom provider\n4. File on Cybercrime.gov.in\n5. Preserve all digital evidence with SHA256 hashes""",
    "kyc":    """KYC Scam Investigation\n\nIndicators:\n• Victim received call claiming KYC expiry\n• Asked to share OTP or install remote app\n• UPI collect request sent disguised as verification\n\nNext Steps:\n1. Collect victim call logs and WhatsApp messages\n2. Trace UPI ID — check PSP and linked bank\n3. Request CCTV if ATM withdrawal involved\n4. File on Cybercrime.gov.in""",
    "66d":    """Section 66D IT Act 2000\n\nCheating by Personation using Computer Resource\nPunishment: Up to 3 years imprisonment + fine up to ₹1 lakh\n\nApplies to:\n• Fake customer care fraud\n• Impersonating bank officials\n• UPI collect request scams\n• Fake government portal fraud\n\nEvidence needed:\n• Call recordings / WhatsApp chats\n• UPI transaction ID and screenshot\n• IP address of fraudster device\n• Victim bank statement""",
    "default":"""PoliceOSINT AI Copilot ready.\n\nI can help with:\n• Draft FIR support notes\n• Explain IPC / IT Act sections\n• UPI fraud investigation steps\n• Crypto tracing methodology\n• MITRE ATT&CK techniques\n• Evidence preservation checklist\n\nType your question to get started.""",
}

def _fallback(messages: List[ChatMessage]) -> str:
    if not messages: return FALLBACKS["default"]
    last = messages[-1].content.lower()
    if any(w in last for w in ["fir","section","ipc","upi","fraud"]): return FALLBACKS["fir"]
    if any(w in last for w in ["kyc","scam","otp"]): return FALLBACKS["kyc"]
    if "66d" in last or "66c" in last: return FALLBACKS["66d"]
    return FALLBACKS["default"]

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in request.messages:
        messages.append({"role": m.role, "content": m.content})

    # Try Groq first (free)
    groq_key = os.environ.get("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None)
    if groq_key and groq_key.startswith("gsk_"):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 1000},
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    return ChatResponse(message=content, model_used="groq/llama-3.3-70b")
                logger.error("Groq error", status=resp.status_code, body=resp.text[:200])
        except Exception as e:
            logger.error("Groq exception", error=str(e))

    # Try OpenAI (if key has credits)
    openai_key = settings.OPENAI_API_KEY
    if openai_key and openai_key.startswith("sk-"):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                    json={"model": "gpt-4o-mini", "messages": messages, "max_tokens": 1000},
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    return ChatResponse(message=content, model_used="gpt-4o-mini")
        except Exception as e:
            logger.error("OpenAI exception", error=str(e))

    # Try Ollama (local)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json={"model": "mistral", "messages": messages, "stream": False},
            )
            if resp.status_code == 200:
                content = resp.json()["message"]["content"]
                return ChatResponse(message=content, model_used="ollama/mistral")
    except Exception:
        pass

    return ChatResponse(message=_fallback(request.messages), model_used="demo-fallback")
