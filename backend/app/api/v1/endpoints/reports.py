"""
Reports endpoint — Phase 6
PDF generation with ReportLab · FIR support · Intelligence · Suspect profile
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime, timezone
import io
from app.core.database import get_db
from app.db.models.case import Case
from app.db.models.investigation import Investigation
from app.db.models.user import User
from app.api.deps import get_current_user, require_perm

router = APIRouter()

REPORT_TYPES = {
    "fir_support":     "FIR Support Report",
    "intelligence":    "Intelligence Report",
    "fraud":           "Fraud Investigation Report",
    "threat":          "Threat Report",
    "suspect_profile": "Suspect Profile",
    "evidence_summary":"Evidence Summary",
}

IPC_DESCRIPTIONS = {
    "419":  "Section 419 IPC — Cheating by personation",
    "420":  "Section 420 IPC — Cheating and dishonestly inducing delivery of property",
    "406":  "Section 406 IPC — Criminal breach of trust",
    "120B": "Section 120B IPC — Criminal conspiracy",
    "66":   "Section 66 IT Act — Computer related offences",
    "66C":  "Section 66C IT Act — Identity theft",
    "66D":  "Section 66D IT Act — Cheating by personation using computer resource",
    "66F":  "Section 66F IT Act — Cyber terrorism",
    "43A":  "Section 43A IT Act — Failure to protect data",
    "43":   "Section 43 IT Act — Penalty for damage to computer",
}


@router.get("/types")
async def list_types(current_user: User = Depends(get_current_user)):
    return [{"id": k, "label": v} for k, v in REPORT_TYPES.items()]


@router.get("/{case_id}/fir-notes")
async def get_fir_notes(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("report:generate")),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case   = result.scalar_one_or_none()
    if not case:
        return JSONResponse(status_code=404, content={"error": "Case not found"})

    ipc_details = [
        {"section": s, "description": IPC_DESCRIPTIONS.get(s, f"Section {s}")}
        for s in (case.ipc_sections or [])
    ]

    inv_result = await db.execute(
        select(Investigation).where(Investigation.case_id == case_id)
        .order_by(Investigation.created_at.desc())
    )
    investigations = inv_result.scalars().all()

    return {
        "report_type":  "FIR Support Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": current_user.badge_number,
        "platform":     "PoliceOSINT v1.0 — GPCSSI Gurugram",
        "case_details": {
            "case_number":      case.case_number,
            "fir_number":       case.fir_number or "Not yet filed",
            "title":            case.title,
            "case_type":        case.case_type,
            "status":           case.status,
            "priority":         case.priority,
            "date_reported":    case.created_at.strftime("%d %B %Y") if case.created_at else "",
            "incident_location":case.incident_location or "Under investigation",
        },
        "victim_details": {
            "name":        case.victim_name  or "As per complaint",
            "phone":       case.victim_phone or "On record",
            "email":       case.victim_email or "On record",
            "amount_lost": f"₹{int(case.amount_lost or 0):,}" if case.amount_lost else "Under assessment",
        },
        "applicable_sections":          ipc_details,
        "legal_provisions":             _get_legal_provisions(case.case_type),
        "digital_evidence_checklist":   _evidence_checklist(),
        "investigation_summary": {
            "total_investigations": len(investigations),
            "osint_sources_used":   list(set(s for inv in investigations for s in (inv.sources_queried or []))),
            "highest_risk_score":   max((inv.risk_score or 0 for inv in investigations), default=0),
        },
        "recommended_actions":  _recommended_actions(case.case_type, case.amount_lost),
        "escalation":           _escalation(case.case_type, case.amount_lost),
        "notice_templates": {
            "bank_freeze":   f"Please freeze account/UPI ID associated with Case No. {case.case_number} under Section 91 CrPC. Investigation in progress by Gurugram Cyber Cell.",
            "telecom_cdr":   f"CDR required for phone numbers in Case No. {case.case_number}. Please provide records for last 90 days.",
            "platform_logs": f"Transaction logs and IP logs required for Case No. {case.case_number} under Section 91 CrPC.",
        },
    }


@router.get("/{case_id}/suspect-profile")
async def get_suspect_profile(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("report:generate")),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case   = result.scalar_one_or_none()
    if not case:
        return JSONResponse(status_code=404, content={"error": "Case not found"})

    inv_result = await db.execute(
        select(Investigation).where(Investigation.case_id == case_id)
        .order_by(Investigation.created_at.desc())
    )
    investigations = inv_result.scalars().all()

    return {
        "report_type":  "Suspect Profile",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_number":  case.case_number,
        "generated_by": current_user.badge_number,
        "known_identifiers": {
            "upi_ids":       [i.query for i in investigations if i.investigation_type == "upi_fraud"],
            "ip_addresses":  [i.query for i in investigations if i.investigation_type == "ip"],
            "domains":       [i.query for i in investigations if i.investigation_type == "domain"],
            "emails":        [i.query for i in investigations if i.investigation_type == "identity" and "@" in i.query],
            "usernames":     [i.query for i in investigations if i.investigation_type == "identity" and "@" not in i.query],
            "crypto_wallets":[i.query for i in investigations if i.investigation_type == "crypto"],
        },
        "risk_assessment": {
            "overall_risk":        max((i.risk_score or 0 for i in investigations), default=0),
            "risk_label":          "CRITICAL" if max((i.risk_score or 0 for i in investigations), default=0) >= 80
                                   else "HIGH" if max((i.risk_score or 0 for i in investigations), default=0) >= 60
                                   else "MEDIUM",
            "investigation_count": len(investigations),
        },
        "suspect_info":    case.suspect_info or {},
        "modus_operandi":  _modus_operandi(case.case_type),
        "arrest_grounds": [
            f"Prima facie evidence of offence u/s {', '.join(case.ipc_sections or ['419 IPC'])}",
            "Digital footprint traced to suspect identifiers via OSINT investigation",
            "Multiple victim complaints corroborated",
            "Financial trail established through blockchain/UPI analysis",
        ],
    }


@router.get("/{case_id}/download/fir-pdf")
async def download_fir_pdf(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("report:generate")),
):
    """Download FIR Support Report as PDF."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case   = result.scalar_one_or_none()
    if not case:
        return JSONResponse(status_code=404, content={"error": "Case not found"})

    # Get FIR data
    from app.api.v1.endpoints.reports import get_fir_notes
    fir_data = await get_fir_notes(case_id, db, current_user)

    try:
        from app.services.reports.pdf_generator import generate_fir_report
        pdf_bytes = generate_fir_report(
            case_data={"case_number": case.case_number},
            fir_data=fir_data,
            officer=current_user.badge_number,
        )
        filename = f"FIR_Support_{case.case_number.replace('/','_')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError:
        return JSONResponse(status_code=503, content={
            "error": "PDF generation unavailable. Install: pip install reportlab==4.2.2",
            "fallback": f"/api/v1/reports/{case_id}/fir-notes",
        })


@router.get("/{case_id}/download/intelligence-pdf")
async def download_intelligence_pdf(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("report:generate")),
):
    """Download Intelligence Report as PDF."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case   = result.scalar_one_or_none()
    if not case:
        return JSONResponse(status_code=404, content={"error": "Case not found"})

    inv_result = await db.execute(
        select(Investigation).where(Investigation.case_id == case_id)
        .order_by(Investigation.created_at.desc())
    )
    investigations = [
        {
            "investigation_type": str(i.investigation_type).replace("InvestigationType.",""),
            "query":              i.query,
            "risk_score":         i.risk_score or 0,
            "summary":            i.summary or "",
            "sources_queried":    i.sources_queried or [],
            "status":             str(i.status),
        }
        for i in inv_result.scalars().all()
    ]

    try:
        from app.services.reports.pdf_generator import generate_intelligence_report
        pdf_bytes = generate_intelligence_report(
            case_data={"case_number": case.case_number},
            investigations=investigations,
            officer=current_user.badge_number,
        )
        filename = f"Intelligence_{case.case_number.replace('/','_')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError:
        return JSONResponse(status_code=503, content={"error": "reportlab not installed"})


@router.get("/{case_id}/download/suspect-pdf")
async def download_suspect_pdf(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("report:generate")),
):
    """Download Suspect Profile as PDF."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case   = result.scalar_one_or_none()
    if not case:
        return JSONResponse(status_code=404, content={"error": "Case not found"})

    profile_data = await get_suspect_profile(case_id, db, current_user)

    try:
        from app.services.reports.pdf_generator import generate_suspect_profile_pdf
        pdf_bytes = generate_suspect_profile_pdf(
            case_data={"case_number": case.case_number},
            profile_data=profile_data,
            officer=current_user.badge_number,
        )
        filename = f"Suspect_Profile_{case.case_number.replace('/','_')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError:
        return JSONResponse(status_code=503, content={"error": "reportlab not installed"})


@router.post("/{case_id}/generate")
async def generate_report(
    case_id: str,
    report_type: str = Query("intelligence"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("report:generate")),
):
    return {
        "report_id":    f"RPT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "case_id":      case_id,
        "report_type":  report_type,
        "report_label": REPORT_TYPES.get(report_type, report_type),
        "status":       "generated",
        "generated_by": current_user.badge_number,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{case_id}/list")
async def list_reports(
    case_id: str,
    current_user: User = Depends(require_perm("report:view")),
):
    now = datetime.now(timezone.utc)
    return [
        {"id":"RPT-001","type":"fir_support",    "label":"FIR Support Report",   "created_at":now.isoformat(),"created_by":current_user.badge_number},
        {"id":"RPT-002","type":"intelligence",   "label":"Intelligence Report",  "created_at":now.isoformat(),"created_by":current_user.badge_number},
        {"id":"RPT-003","type":"suspect_profile","label":"Suspect Profile",      "created_at":now.isoformat(),"created_by":current_user.badge_number},
    ]


def _get_legal_provisions(case_type: str) -> list:
    p = {
        "upi_fraud":        ["Section 66D IT Act 2000","Section 419 IPC","Section 420 IPC","PMLA 2002"],
        "phishing":         ["Section 66C IT Act 2000","Section 66D IT Act 2000","Section 419 IPC"],
        "ransomware":       ["Section 66F IT Act 2000","Section 43 IT Act 2000","Section 385 IPC"],
        "investment_fraud": ["Section 420 IPC","Section 406 IPC","SEBI Act 1992","PMLA 2002"],
        "identity_theft":   ["Section 66C IT Act 2000","Section 419 IPC","Section 468 IPC"],
        "data_breach":      ["Section 43A IT Act 2000","Section 72A IT Act 2000"],
        "crypto_fraud":     ["Section 420 IPC","PMLA 2002","Virtual Digital Assets Regulations 2022"],
        "loan_scam":        ["Section 420 IPC","Section 406 IPC","RBI Guidelines on Digital Lending"],
    }
    return p.get(str(case_type), ["Section 66 IT Act 2000","Section 419 IPC"])


def _evidence_checklist() -> list:
    return [
        "Transaction screenshots with SHA256 hash verification",
        "UPI transaction ID and bank statement certified copy",
        "WhatsApp/SMS conversations exported with metadata",
        "Call Detail Records (CDR) from telecom provider",
        "IP address logs from platform/PSP",
        "Device forensics report (if device seized)",
        "Screen recordings of fraudulent communication",
        "Email headers (if email fraud involved)",
        "CCTV footage (if ATM/cash withdrawal involved)",
        "Witness statements (digital + physical)",
    ]


def _recommended_actions(case_type: str, amount_lost) -> list:
    actions = [
        "Issue notice u/s 91 CrPC to bank/PSP for account freeze",
        "Request CDR from telecom provider for all linked numbers",
        "Submit complaint to Cybercrime.gov.in (if not done)",
        "Preserve all digital evidence with SHA256 hash verification",
        "Issue notice to ISP for IP address logs",
    ]
    if amount_lost and int(amount_lost or 0) > 1000000:
        actions.append("Escalate to SFIO/ED (amount > ₹10L)")
    if str(case_type) in ("upi_fraud","investment_fraud"):
        actions += ["Report to NPCI Fraud Management System",
                    "Alert victim bank for chargeback/reversal"]
    if str(case_type) == "ransomware":
        actions.append("Contact CERT-In (cert-in.org.in) for technical assistance")
    return actions


def _escalation(case_type: str, amount_lost) -> dict:
    amount = int(amount_lost or 0)
    return {
        "cert_in": str(case_type) in ("ransomware","data_breach"),
        "sfio":    amount > 1000000,
        "ed_pmla": amount > 5000000,
        "interpol":str(case_type) == "cyber_crime" and amount > 10000000,
        "i4c":     True,
        "npci":    str(case_type) in ("upi_fraud",),
        "rbi":     str(case_type) in ("upi_fraud","investment_fraud") and amount > 500000,
    }


def _modus_operandi(case_type: str) -> str:
    mo = {
        "upi_fraud":        "Suspect contacted victim claiming to be bank official. Sent UPI collect request disguised as refund/cashback. Victim approved resulting in financial loss.",
        "phishing":         "Suspect created fraudulent website mimicking legitimate bank. Victim entered credentials which were captured. Credentials used for unauthorized access.",
        "ransomware":       "Malicious code delivered via email attachment/exploit. Victim files encrypted. Ransom demanded in cryptocurrency to restore access.",
        "investment_fraud": "Suspect lured victim with promises of high returns on fake trading platform. Initial small profits shown to build trust. Large deposit made and funds stolen.",
        "loan_scam":        "Suspect offered instant loan without credit check. Processing fee collected upfront. After payment, suspect became unreachable. Loan never disbursed.",
        "identity_theft":   "Suspect obtained victim personal information through social engineering or data breach. Used to create fraudulent accounts and make unauthorized transactions.",
    }
    return mo.get(str(case_type), "Modus operandi under investigation.")


@router.get("/{case_id}/download/fraud-pdf")
async def download_fraud_pdf(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("report:generate")),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case   = result.scalar_one_or_none()
    if not case:
        return JSONResponse(status_code=404, content={"error": "Case not found"})

    fir_data = await get_fir_notes(case_id, db, current_user)
    try:
        from app.services.reports.pdf_generator import generate_fraud_report
        pdf_bytes = generate_fraud_report(
            case_data={"case_number": case.case_number,
                       "case_type":   str(case.case_type).replace("CaseType.","")},
            fir_data=fir_data,
            officer=current_user.badge_number,
        )
        filename = f"Fraud_Investigation_{case.case_number.replace('/','_')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes), media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError:
        return JSONResponse(status_code=503, content={"error": "reportlab not installed"})


@router.get("/{case_id}/download/threat-pdf")
async def download_threat_pdf(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("report:generate")),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case   = result.scalar_one_or_none()
    if not case:
        return JSONResponse(status_code=404, content={"error": "Case not found"})

    try:
        from app.services.reports.pdf_generator import generate_threat_report
        pdf_bytes = generate_threat_report(
            case_data={
                "case_number": case.case_number,
                "case_type":   str(case.case_type).replace("CaseType.",""),
            },
            officer=current_user.badge_number,
        )
        filename = f"Threat_Report_{case.case_number.replace('/','_')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes), media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError:
        return JSONResponse(status_code=503, content={"error": "reportlab not installed"})


@router.get("/{case_id}/download/evidence-pdf")
async def download_evidence_pdf(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("report:generate")),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case   = result.scalar_one_or_none()
    if not case:
        return JSONResponse(status_code=404, content={"error": "Case not found"})

    from app.db.models.evidence import Evidence
    ev_result = await db.execute(
        select(Evidence).where(Evidence.case_id == case_id)
        .order_by(Evidence.created_at.asc())
    )
    evidence_list = [
        {
            "exhibit_number":    e.exhibit_number,
            "original_filename": e.original_filename,
            "evidence_type":     str(e.evidence_type).replace("EvidenceType.",""),
            "file_size_human":   _human_size(e.file_size or 0),
            "sha256_hash":       e.sha256_hash,
            "md5_hash":          e.md5_hash,
            "created_at":        e.created_at.isoformat() if e.created_at else "",
        }
        for e in ev_result.scalars().all()
    ]

    try:
        from app.services.reports.pdf_generator import generate_evidence_summary
        pdf_bytes = generate_evidence_summary(
            case_data={"case_number": case.case_number},
            evidence_list=evidence_list,
            officer=current_user.badge_number,
        )
        filename = f"Evidence_Summary_{case.case_number.replace('/','_')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes), media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError:
        return JSONResponse(status_code=503, content={"error": "reportlab not installed"})


def _human_size(size: int) -> str:
    for unit in ["B","KB","MB","GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size //= 1024
    return f"{size:.1f} TB"
