import io, json, os
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

# Resolve template dir relative to this file
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates", "reports")

_jinja_env = None

def _get_env():
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=select_autoescape(["html"]),
        )
        _jinja_env.filters["tojson"] = lambda v, **kw: json.dumps(v, **kw)
        _jinja_env.filters["truncate"] = lambda s, n=80, **kw: str(s)[:n] + "…" if len(str(s)) > n else str(s)
    return _jinja_env


IPC_DESCRIPTIONS = {
    "419":  {"act": "IPC",    "description": "Cheating by personation",                                        "applicability": "Suspect impersonated bank/official"},
    "420":  {"act": "IPC",    "description": "Cheating and dishonestly inducing delivery",                     "applicability": "Financial fraud / inducing victim to pay"},
    "468":  {"act": "IPC",    "description": "Forgery for purpose of cheating",                                "applicability": "Fake documents used in fraud"},
    "471":  {"act": "IPC",    "description": "Using as genuine a forged document",                             "applicability": "Forged documents presented as genuine"},
    "406":  {"act": "IPC",    "description": "Criminal breach of trust",                                       "applicability": "Entrusted money not returned"},
    "66C":  {"act": "IT Act", "description": "Identity theft",                                                 "applicability": "Misuse of electronic signature/password/ID"},
    "66D":  {"act": "IT Act", "description": "Cheating by personation using computer resource",                "applicability": "Online impersonation / phishing"},
    "66F":  {"act": "IT Act", "description": "Cyber terrorism",                                                "applicability": "Ransomware / critical infrastructure attack"},
    "43":   {"act": "IT Act", "description": "Penalty for damage to computer system",                         "applicability": "Unauthorised access / data theft"},
    "43A":  {"act": "IT Act", "description": "Compensation for failure to protect data",                      "applicability": "Data breach / negligent data handling"},
    "72A":  {"act": "IT Act", "description": "Punishment for disclosure of information in breach of contract","applicability": "Data leak by insider"},
}


def _resolve_ipc(sections: list) -> list:
    result = []
    for s in sections:
        s = str(s).strip()
        if s in IPC_DESCRIPTIONS:
            result.append({"section": s, **IPC_DESCRIPTIONS[s]})
        else:
            result.append({"section": s, "act": "IPC/IT Act", "description": "Refer to statute", "applicability": "As applicable"})
    return result


def _ref(case_number: str, report_type: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    return f"POI/{report_type.upper()[:3]}/{case_number}/{ts}"


def _render_pdf(template_name: str, context: dict) -> bytes:
    env = _get_env()
    tmpl = env.get_template(template_name)
    html_str = tmpl.render(**context)
    pdf_bytes = HTML(string=html_str, base_url=TEMPLATE_DIR).write_pdf()
    return pdf_bytes


def generate_fir_support(case, investigations, evidence_list, officer) -> bytes:
    steps = [
        "Record victim statement under Section 161 CrPC",
        "Issue u/s 91 CrPC notice to bank/PSP for account freeze and transaction logs",
        "Issue u/s 91 CrPC notice to telecom provider for CDR and IMEI data",
        "File complaint on Cybercrime.gov.in and obtain acknowledgement number",
        "Forward case to I4C if amount exceeds Rs 1 lakh",
        "Collect device(s) used by victim for forensic examination",
        "Verify SHA256 hash of all digital evidence before submission",
        "Obtain certified copy of bank statement from victim",
    ]
    ctx = {
        "case":              case,
        "investigations":    investigations,
        "evidence_list":     evidence_list,
        "ipc_sections":      _resolve_ipc(getattr(case, "ipc_sections", []) or []),
        "officer_name":      getattr(officer, "full_name", "Investigating Officer"),
        "officer_badge":     getattr(officer, "badge_number", "—"),
        "officer_station":   getattr(officer, "station_name", "Gurugram Cyber Cell"),
        "generated_at":      datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC"),
        "report_ref":        _ref(case.case_number, "fir"),
        "notice_bank":       "Concerned Bank / PSP",
        "recommended_steps": steps,
    }
    return _render_pdf("fir_support.html", ctx)


def generate_intelligence(case, investigations, officer) -> bytes:
    risk_scores = [i.risk_score or 0 for i in investigations]
    overall_risk = int(max(risk_scores)) if risk_scores else 0
    iocs, mitre = [], []
    for inv in investigations:
        iocs.append({
            "type":   inv.investigation_type,
            "value":  inv.query,
            "risk":   "HIGH" if (inv.risk_score or 0) >= 70 else "MEDIUM" if (inv.risk_score or 0) >= 40 else "LOW",
            "source": "PoliceOSINT",
        })
        for r in (getattr(inv, "results", None) or []):
            pd = r.parsed_data or {}
            for t in pd.get("techniques", []):
                mitre.append({"id": t.get("id",""), "name": t.get("name",""), "tactic": t.get("tactic",""), "description": t.get("description","")})
    ctx = {
        "case":              case,
        "investigations":    investigations,
        "overall_risk":      overall_risk,
        "executive_summary": f"Intelligence analysis of {len(investigations)} investigation(s) linked to case {case.case_number}. Overall risk: {overall_risk}/100.",
        "iocs":              iocs,
        "mitre_techniques":  mitre,
        "recommendations":   [
            "Block identified IOCs at perimeter firewall and email gateway",
            "Issue preservation notices to all identified platforms within 24 hours",
            "Submit IOC list to CERT-In for national threat sharing",
            "Run internal scan for identified malware hashes across department endpoints",
        ],
        "officer_name":    getattr(officer, "full_name", "Investigating Officer"),
        "officer_badge":   getattr(officer, "badge_number", "—"),
        "officer_station": getattr(officer, "station_name", "Gurugram Cyber Cell"),
        "generated_at":    datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC"),
        "report_ref":      _ref(case.case_number, "intel"),
    }
    return _render_pdf("intelligence.html", ctx)


def generate_fraud(case, investigations, officer) -> bytes:
    victims = [{"name": case.victim_name or "Victim", "contact": case.victim_phone or "—",
                "amount": case.amount_lost or "0", "date": str(case.created_at)[:10], "mode": "UPI / Online Transfer"}]
    accounts = [{"id": "Primary UPI / Account", "psp": "As per investigation", "role": "Primary",
                 "amount": case.amount_lost or "0", "action": "Freeze immediately u/s 102 CrPC"}]
    ctx = {
        "case":               case,
        "total_loss":         f"Rs {case.amount_lost}" if case.amount_lost else "Under assessment",
        "victim_count":       1,
        "mule_count":         len([i for i in investigations if str(i.investigation_type) == "upi"]),
        "fraud_summary":      f"Fraud investigation for case {case.case_number}. {case.title}.",
        "victims":            victims,
        "accounts":           accounts,
        "modus_operandi":     case.description or "Under investigation.",
        "recommended_actions": [
            "Issue immediate freeze order to PSP u/s 102 CrPC",
            "File on cybercrime.gov.in and call 1930 helpline",
            "Obtain CCTV footage from ATM/location if cash withdrawal involved",
            "Collect victim phone for forensic analysis of fraud call/message",
        ],
        "officer_name":    getattr(officer, "full_name", "Investigating Officer"),
        "officer_badge":   getattr(officer, "badge_number", "—"),
        "officer_station": getattr(officer, "station_name", "Gurugram Cyber Cell"),
        "generated_at":    datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC"),
        "report_ref":      _ref(case.case_number, "fraud"),
    }
    return _render_pdf("fraud.html", ctx)


def generate_threat(case, investigations, officer) -> bytes:
    threat_inv = next((i for i in investigations if str(i.investigation_type) == "threat"), None)
    risk  = int(threat_inv.risk_score or 0) if threat_inv else 0
    level = "CRITICAL" if risk >= 80 else "HIGH" if risk >= 60 else "MEDIUM" if risk >= 40 else "LOW"
    iocs  = [{"type": str(i.investigation_type), "value": i.query,
               "confidence": "HIGH" if (i.risk_score or 0) >= 70 else "MEDIUM"} for i in investigations]
    ctx = {
        "case":             case,
        "threat_actor":     "Under Investigation",
        "threat_level":     level,
        "malware_family":   None,
        "campaign":         None,
        "threat_summary":   f"Threat analysis for case {case.case_number}. Risk level: {level}.",
        "actor_profile":    {"Origin": "Unknown", "Motivation": "Financial", "Sophistication": "Medium"},
        "mitre_techniques": [],
        "iocs":             iocs,
        "countermeasures":  [
            "Block IOCs at firewall and endpoint protection",
            "Enable enhanced logging on affected systems",
            "Report to CERT-In within 6 hours if ransomware/APT",
            "Preserve memory dumps before remediation",
        ],
        "escalation_note":  "Escalate to CERT-In (cert-in.org.in) if critical infrastructure is affected.",
        "officer_name":    getattr(officer, "full_name", "Investigating Officer"),
        "officer_badge":   getattr(officer, "badge_number", "—"),
        "officer_station": getattr(officer, "station_name", "Gurugram Cyber Cell"),
        "generated_at":    datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC"),
        "report_ref":      _ref(case.case_number, "threat"),
    }
    return _render_pdf("threat.html", ctx)


def generate_suspect_profile(case, investigations, officer) -> bytes:
    identifiers  = [{"type": str(i.investigation_type), "value": i.query,
                     "platform": "Digital", "verified": i.status == "completed"} for i in investigations]
    risk_scores  = [i.risk_score or 0 for i in investigations]
    overall      = int(max(risk_scores)) if risk_scores else 0
    ctx = {
        "case": case,
        "suspect": {
            "risk_score":      overall,
            "identifiers":     identifiers,
            "risk_factors":    [{"factor": "Digital Footprint", "score": overall, "details": "Based on OSINT investigation results"}],
            "online_presence": [{"platform": str(i.investigation_type), "username": i.query,
                                 "status": "Active", "notes": i.summary} for i in investigations[:5]],
            "modus_operandi":  case.description or "Under investigation.",
            "arrest_grounds":  f"Digital evidence linking suspect to case {case.case_number} through OSINT investigation.",
            "legal_grounds":   [f"Section {s} IPC/IT Act" for s in (getattr(case, "ipc_sections", []) or [])],
            "associates":      [],
        },
        "officer_name":    getattr(officer, "full_name", "Investigating Officer"),
        "officer_badge":   getattr(officer, "badge_number", "—"),
        "officer_station": getattr(officer, "station_name", "Gurugram Cyber Cell"),
        "generated_at":    datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC"),
        "report_ref":      _ref(case.case_number, "suspect"),
    }
    return _render_pdf("suspect_profile.html", ctx)
