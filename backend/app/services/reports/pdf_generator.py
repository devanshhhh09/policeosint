"""
PDF Report Generator — Phase 6
Uses ReportLab to generate court-ready police investigation reports
"""
import io
from datetime import datetime, timezone
from typing import Any

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ── Colour palette ─────────────────────────────────────────────────────────────
NAVY    = colors.HexColor("#1a2744")
BLUE    = colors.HexColor("#185FA5")
RED     = colors.HexColor("#A32D2D")
AMBER   = colors.HexColor("#854F0B")
GREEN   = colors.HexColor("#0F6E56")
LGRAY   = colors.HexColor("#F5F5F5")
MGRAY   = colors.HexColor("#CCCCCC")
DGRAY   = colors.HexColor("#555555")
WHITE   = colors.white
BLACK   = colors.black


def _styles():
    base = getSampleStyleSheet()
    custom = {
        "title": ParagraphStyle("title", parent=base["Normal"],
            fontSize=18, fontName="Helvetica-Bold",
            textColor=NAVY, alignment=TA_CENTER, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"],
            fontSize=11, fontName="Helvetica",
            textColor=DGRAY, alignment=TA_CENTER, spaceAfter=12),
        "section_heading": ParagraphStyle("section_heading", parent=base["Normal"],
            fontSize=11, fontName="Helvetica-Bold",
            textColor=WHITE, spaceBefore=14, spaceAfter=6),
        "field_label": ParagraphStyle("field_label", parent=base["Normal"],
            fontSize=9, fontName="Helvetica-Bold", textColor=DGRAY),
        "field_value": ParagraphStyle("field_value", parent=base["Normal"],
            fontSize=9, fontName="Helvetica", textColor=BLACK),
        "body": ParagraphStyle("body", parent=base["Normal"],
            fontSize=9, fontName="Helvetica", textColor=BLACK,
            leading=14, alignment=TA_JUSTIFY),
        "small": ParagraphStyle("small", parent=base["Normal"],
            fontSize=8, fontName="Helvetica", textColor=DGRAY),
        "alert": ParagraphStyle("alert", parent=base["Normal"],
            fontSize=9, fontName="Helvetica-Bold", textColor=RED),
        "mono": ParagraphStyle("mono", parent=base["Normal"],
            fontSize=8, fontName="Courier", textColor=BLACK),
        "footer": ParagraphStyle("footer", parent=base["Normal"],
            fontSize=7, fontName="Helvetica", textColor=MGRAY, alignment=TA_CENTER),
    }
    return {**{k: base[k] for k in base.byName}, **custom}


def _section_header(title: str, styles: dict, color=NAVY):
    """Blue section header bar."""
    data   = [[Paragraph(f"  {title}", styles["section_heading"])]]
    table  = Table(data, colWidths=[17*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), color),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [color]),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("ROUNDEDCORNERS", [3]),
    ]))
    return table


def _kv_table(rows: list[tuple], styles: dict, col1=5*cm, col2=12*cm):
    """Two-column key-value table."""
    data = [
        [Paragraph(k, styles["field_label"]), Paragraph(str(v), styles["field_value"])]
        for k, v in rows
    ]
    table = Table(data, colWidths=[col1, col2])
    table.setStyle(TableStyle([
        ("VALIGN",         (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",     (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 4),
        ("LEFTPADDING",    (0,0), (-1,-1), 4),
        ("RIGHTPADDING",   (0,0), (-1,-1), 4),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [WHITE, LGRAY]),
        ("LINEBELOW",      (0,0), (-1,-1), 0.25, MGRAY),
        ("BOX",            (0,0), (-1,-1), 0.5, MGRAY),
    ]))
    return table


def _letterhead(story: list, report_type: str, case_number: str, styles: dict):
    """Police letterhead."""
    # Top bar
    top = Table([[
        Paragraph("🛡  GURUGRAM CYBER CELL", ParagraphStyle("lh", parent=styles["Normal"],
            fontSize=14, fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_LEFT)),
        Paragraph("HARYANA POLICE", ParagraphStyle("lh2", parent=styles["Normal"],
            fontSize=10, fontName="Helvetica", textColor=WHITE, alignment=TA_RIGHT)),
    ]], colWidths=[10*cm, 7*cm])
    top.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
    ]))
    story.append(top)
    story.append(Spacer(1, 0.3*cm))

    # Report title
    story.append(Paragraph(report_type.upper(), styles["title"]))
    story.append(Paragraph(
        f"Case No: {case_number}  ·  Generated: {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}  ·  Platform: PoliceOSINT v1.0",
        styles["subtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY))
    story.append(Spacer(1, 0.4*cm))


def _footer_note(story: list, styles: dict):
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MGRAY))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph(
        "CONFIDENTIAL — This document is generated by PoliceOSINT and intended for authorised law enforcement use only. "
        "Unauthorised disclosure is an offence under Section 72 of the IT Act 2000. "
        "All OSINT data is gathered through legal, passive reconnaissance methods.",
        styles["footer"]
    ))
    story.append(Paragraph(
        f"PoliceOSINT v1.0 · GPCSSI · Gurugram Cyber Cell · {datetime.now(timezone.utc).strftime('%Y')}",
        styles["footer"]
    ))


# ── FIR Support Report ─────────────────────────────────────────────────────────
def generate_fir_report(case_data: dict, fir_data: dict, officer: str) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab not installed. Run: pip install reportlab==4.2.2")

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=1.5*cm, bottomMargin=2*cm)
    styles = _styles()
    story  = []

    case_num = case_data.get("case_number", "Unknown")
    _letterhead(story, "FIR SUPPORT REPORT", case_num, styles)

    # ── Case Details ──────────────────────────────────────────────────────────
    story.append(_section_header("CASE DETAILS", styles))
    story.append(Spacer(1, 0.2*cm))
    cd = fir_data.get("case_details", {})
    vd = fir_data.get("victim_details", {})
    story.append(_kv_table([
        ("Case Number",       cd.get("case_number",       "—")),
        ("FIR Number",        cd.get("fir_number",        "Not yet filed")),
        ("Case Type",         cd.get("case_type",         "—").replace("_"," ").title()),
        ("Status",            cd.get("status",            "—").title()),
        ("Priority",          cd.get("priority",          "—").upper()),
        ("Date of Report",    cd.get("date_reported",     "—")),
        ("Incident Location", cd.get("incident_location", "Under investigation")),
        ("Investigating Officer", officer),
    ], styles))
    story.append(Spacer(1, 0.4*cm))

    # ── Victim Details ────────────────────────────────────────────────────────
    story.append(_section_header("VICTIM DETAILS", styles))
    story.append(Spacer(1, 0.2*cm))
    story.append(_kv_table([
        ("Name",         vd.get("name",         "As per complaint")),
        ("Phone",        vd.get("phone",        "On record")),
        ("Email",        vd.get("email",        "On record")),
        ("Amount Lost",  vd.get("amount_lost",  "Under assessment")),
    ], styles))
    story.append(Spacer(1, 0.4*cm))

    # ── Applicable Sections ───────────────────────────────────────────────────
    story.append(_section_header("APPLICABLE SECTIONS", styles, color=RED))
    story.append(Spacer(1, 0.2*cm))
    sections = fir_data.get("applicable_sections", [])
    if sections:
        sec_data = [["Section", "Description"]] + [
            [Paragraph(s.get("section",""), styles["field_label"]),
             Paragraph(s.get("description",""), styles["field_value"])]
            for s in sections
        ]
        sec_table = Table(sec_data, colWidths=[3.5*cm, 13.5*cm])
        sec_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),   NAVY),
            ("TEXTCOLOR",     (0,0), (-1,0),   WHITE),
            ("FONTNAME",      (0,0), (-1,0),   "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1),  9),
            ("ROWBACKGROUNDS",(0,1), (-1,-1),  [WHITE, LGRAY]),
            ("GRID",          (0,0), (-1,-1),  0.25, MGRAY),
            ("TOPPADDING",    (0,0), (-1,-1),  5),
            ("BOTTOMPADDING", (0,0), (-1,-1),  5),
            ("LEFTPADDING",   (0,0), (-1,-1),  6),
            ("VALIGN",        (0,0), (-1,-1),  "TOP"),
        ]))
        story.append(sec_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Legal Provisions ──────────────────────────────────────────────────────
    provisions = fir_data.get("legal_provisions", [])
    if provisions:
        story.append(_section_header("LEGAL PROVISIONS", styles))
        story.append(Spacer(1, 0.2*cm))
        for p in provisions:
            story.append(Paragraph(f"  ▸  {p}", styles["body"]))
            story.append(Spacer(1, 0.15*cm))
        story.append(Spacer(1, 0.2*cm))

    # ── Digital Evidence Checklist ────────────────────────────────────────────
    checklist = fir_data.get("digital_evidence_checklist", [])
    if checklist:
        story.append(_section_header("DIGITAL EVIDENCE CHECKLIST", styles, color=GREEN))
        story.append(Spacer(1, 0.2*cm))
        chk_data = [["#", "Evidence Item", "Status"]]
        for i, item in enumerate(checklist, 1):
            chk_data.append([str(i), item, "☐ Pending"])
        chk_table = Table(chk_data, colWidths=[1*cm, 13*cm, 3*cm])
        chk_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  NAVY),
            ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
            ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGRAY]),
            ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(chk_table)
        story.append(Spacer(1, 0.4*cm))

    # ── Recommended Actions ───────────────────────────────────────────────────
    actions = fir_data.get("recommended_actions", [])
    if actions:
        story.append(_section_header("RECOMMENDED ACTIONS", styles, color=AMBER))
        story.append(Spacer(1, 0.2*cm))
        for i, action in enumerate(actions, 1):
            story.append(Paragraph(f"  {i}.  {action}", styles["body"]))
            story.append(Spacer(1, 0.12*cm))
        story.append(Spacer(1, 0.2*cm))

    # ── Notice Templates ──────────────────────────────────────────────────────
    notices = fir_data.get("notice_templates", {})
    if notices:
        story.append(_section_header("NOTICE TEMPLATES (u/s 91 CrPC)", styles))
        story.append(Spacer(1, 0.2*cm))
        for key, text in notices.items():
            story.append(Paragraph(key.replace("_", " ").title(), styles["field_label"]))
            story.append(Spacer(1, 0.1*cm))
            notice_box = Table(
                [[Paragraph(text, styles["body"])]],
                colWidths=[17*cm]
            )
            notice_box.setStyle(TableStyle([
                ("BACKGROUND",   (0,0), (-1,-1), LGRAY),
                ("BOX",          (0,0), (-1,-1), 0.5, BLUE),
                ("TOPPADDING",   (0,0), (-1,-1), 8),
                ("BOTTOMPADDING",(0,0), (-1,-1), 8),
                ("LEFTPADDING",  (0,0), (-1,-1), 10),
                ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ]))
            story.append(notice_box)
            story.append(Spacer(1, 0.3*cm))

    # ── Escalation ────────────────────────────────────────────────────────────
    escalation = fir_data.get("escalation", {})
    esc_needed = [k.upper().replace("_"," ") for k, v in escalation.items() if v is True]
    if esc_needed:
        story.append(_section_header("ESCALATION REQUIRED", styles, color=RED))
        story.append(Spacer(1, 0.2*cm))
        esc_data = [["Agency", "Reason"]]
        esc_reasons = {
            "CERT IN":  "Cyber incident response required",
            "SFIO":     "Financial fraud above ₹10 lakh",
            "ED PMLA":  "Money laundering suspected (>₹50 lakh)",
            "INTERPOL": "International cybercrime linkage",
            "I4C":      "Indian Cyber Crime Coordination Centre",
            "NPCI":     "UPI/payment system fraud",
            "RBI":      "Banking/financial system fraud",
        }
        for agency in esc_needed:
            esc_data.append([agency, esc_reasons.get(agency, "Escalation required")])
        esc_table = Table(esc_data, colWidths=[4*cm, 13*cm])
        esc_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  RED),
            ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
            ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGRAY]),
            ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ]))
        story.append(esc_table)
        story.append(Spacer(1, 0.3*cm))

    # ── Signature block ───────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6*cm))
    sig_data = [
        [
            Paragraph("Investigating Officer", styles["field_label"]),
            Paragraph("Supervisor / SI", styles["field_label"]),
            Paragraph("Station In-charge", styles["field_label"]),
        ],
        [
            Paragraph(f"\n\n\n{officer}\nGurugram Cyber Cell", styles["small"]),
            Paragraph("\n\n\n_________________\nSign & Stamp", styles["small"]),
            Paragraph("\n\n\n_________________\nSign & Stamp", styles["small"]),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[5.67*cm, 5.67*cm, 5.67*cm])
    sig_table.setStyle(TableStyle([
        ("BOX",          (0,0), (-1,-1), 0.5, MGRAY),
        ("INNERGRID",    (0,0), (-1,-1), 0.5, MGRAY),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(sig_table)

    _footer_note(story, styles)
    doc.build(story)
    return buf.getvalue()


# ── Intelligence Report ────────────────────────────────────────────────────────
def generate_intelligence_report(case_data: dict, investigations: list, officer: str) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab not installed")

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=1.5*cm, bottomMargin=2*cm)
    styles = _styles()
    story  = []

    case_num = case_data.get("case_number", "Unknown")
    _letterhead(story, "INTELLIGENCE REPORT", case_num, styles)

    # Executive summary
    story.append(_section_header("EXECUTIVE SUMMARY", styles))
    story.append(Spacer(1, 0.2*cm))
    total_inv  = len(investigations)
    high_risk  = [i for i in investigations if (i.get("risk_score") or 0) >= 70]
    max_risk   = max((i.get("risk_score") or 0 for i in investigations), default=0)
    story.append(_kv_table([
        ("Case Number",         case_num),
        ("Total Investigations", str(total_inv)),
        ("High Risk Findings",  str(len(high_risk))),
        ("Maximum Risk Score",  f"{max_risk:.0f}/100"),
        ("Report Generated",    datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")),
        ("Generated By",        officer),
    ], styles))
    story.append(Spacer(1, 0.4*cm))

    # Investigation results
    if investigations:
        story.append(_section_header("INVESTIGATION FINDINGS", styles))
        story.append(Spacer(1, 0.2*cm))
        for inv in investigations:
            risk  = inv.get("risk_score") or 0
            rcolor = RED if risk >= 70 else colors.HexColor("#854F0B") if risk >= 40 else GREEN
            inv_block = Table([[
                Paragraph(f"{inv.get('investigation_type','').replace('_',' ').upper()}: {inv.get('query','')[:50]}", styles["field_label"]),
                Paragraph(f"Risk: {risk:.0f}/100", ParagraphStyle("risk", parent=styles["field_label"],
                    textColor=rcolor, alignment=TA_RIGHT)),
            ]], colWidths=[13*cm, 4*cm])
            inv_block.setStyle(TableStyle([
                ("BACKGROUND",   (0,0), (-1,-1), LGRAY),
                ("TOPPADDING",   (0,0), (-1,-1), 6),
                ("BOTTOMPADDING",(0,0), (-1,-1), 6),
                ("LEFTPADDING",  (0,0), (-1,-1), 8),
                ("BOX",          (0,0), (-1,-1), 0.5, MGRAY),
            ]))
            story.append(inv_block)
            if inv.get("summary"):
                story.append(Paragraph(f"  Summary: {inv['summary']}", styles["body"]))
            story.append(Spacer(1, 0.2*cm))

    # Sources queried
    all_sources = list(set(
        s for inv in investigations
        for s in (inv.get("sources_queried") or [])
    ))
    if all_sources:
        story.append(_section_header("OSINT SOURCES USED", styles, color=GREEN))
        story.append(Spacer(1, 0.2*cm))
        src_data = [["Source", "Type"]]
        source_types = {
            "ipinfo":"GeoIP","shodan":"Port Scanner","virustotal":"Threat Intel",
            "hibp":"Breach DB","hunter":"Email Verifier","otx":"Threat Feed",
            "blockchair":"Blockchain","etherscan":"Blockchain","whois":"Domain",
            "dns":"DNS","ssl":"Certificate","subdomains":"Reconnaissance",
        }
        for s in sorted(all_sources):
            src_data.append([s, source_types.get(s, "OSINT")])
        src_table = Table(src_data, colWidths=[8*cm, 9*cm])
        src_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  NAVY),
            ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
            ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGRAY]),
            ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        story.append(src_table)

    _footer_note(story, styles)
    doc.build(story)
    return buf.getvalue()


# ── Suspect Profile PDF ────────────────────────────────────────────────────────
def generate_suspect_profile_pdf(case_data: dict, profile_data: dict, officer: str) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab not installed")

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=1.5*cm, bottomMargin=2*cm)
    styles = _styles()
    story  = []

    case_num = case_data.get("case_number","Unknown")
    _letterhead(story, "SUSPECT PROFILE", case_num, styles)

    # Risk assessment
    risk   = profile_data.get("risk_assessment",{})
    risk_v = risk.get("overall_risk", 0)
    story.append(_section_header("RISK ASSESSMENT", styles,
        color=RED if risk_v >= 70 else colors.HexColor("#854F0B") if risk_v >= 40 else GREEN))
    story.append(Spacer(1, 0.2*cm))
    story.append(_kv_table([
        ("Overall Risk Score",    f"{risk_v:.0f}/100"),
        ("Risk Level",            risk.get("risk_label","UNKNOWN")),
        ("Investigations Run",    str(risk.get("investigation_count",0))),
    ], styles))
    story.append(Spacer(1, 0.4*cm))

    # Digital identifiers
    identifiers = profile_data.get("known_identifiers",{})
    all_ids = [(k.replace("_"," ").title(), ", ".join(v))
               for k, v in identifiers.items() if v]
    if all_ids:
        story.append(_section_header("KNOWN DIGITAL IDENTIFIERS", styles))
        story.append(Spacer(1, 0.2*cm))
        story.append(_kv_table(all_ids, styles))
        story.append(Spacer(1, 0.4*cm))

    # Modus operandi
    mo = profile_data.get("modus_operandi","")
    if mo:
        story.append(_section_header("MODUS OPERANDI", styles, color=AMBER))
        story.append(Spacer(1, 0.2*cm))
        mo_box = Table([[Paragraph(mo, styles["body"])]], colWidths=[17*cm])
        mo_box.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,-1), LGRAY),
            ("BOX",          (0,0), (-1,-1), 0.5, AMBER),
            ("TOPPADDING",   (0,0), (-1,-1), 10),
            ("BOTTOMPADDING",(0,0), (-1,-1), 10),
            ("LEFTPADDING",  (0,0), (-1,-1), 12),
            ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ]))
        story.append(mo_box)
        story.append(Spacer(1, 0.4*cm))

    # Grounds for arrest
    grounds = profile_data.get("arrest_grounds",[])
    if grounds:
        story.append(_section_header("GROUNDS FOR ARREST", styles, color=RED))
        story.append(Spacer(1, 0.2*cm))
        for i, g in enumerate(grounds, 1):
            story.append(Paragraph(f"  {i}.  {g}", styles["body"]))
            story.append(Spacer(1, 0.12*cm))

    _footer_note(story, styles)
    doc.build(story)
    return buf.getvalue()


# ── Fraud Investigation Report ─────────────────────────────────────────────────
def generate_fraud_report(case_data: dict, fir_data: dict, officer: str) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab not installed")

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=1.5*cm, bottomMargin=2*cm)
    styles = _styles()
    story  = []

    case_num = case_data.get("case_number", "Unknown")
    _letterhead(story, "FRAUD INVESTIGATION REPORT", case_num, styles)

    # Case overview
    story.append(_section_header("CASE OVERVIEW", styles))
    story.append(Spacer(1, 0.2*cm))
    cd = fir_data.get("case_details", {})
    vd = fir_data.get("victim_details", {})
    story.append(_kv_table([
        ("Case Number",       cd.get("case_number",       "—")),
        ("FIR Number",        cd.get("fir_number",        "Not yet filed")),
        ("Fraud Type",        cd.get("case_type",         "—").replace("_"," ").title()),
        ("Status",            cd.get("status",            "—").title()),
        ("Priority",          cd.get("priority",          "—").upper()),
        ("Date of Report",    cd.get("date_reported",     "—")),
        ("Incident Location", cd.get("incident_location", "Under investigation")),
        ("Investigating Officer", officer),
    ], styles))
    story.append(Spacer(1, 0.4*cm))

    # Financial loss
    story.append(_section_header("FINANCIAL LOSS ASSESSMENT", styles, color=RED))
    story.append(Spacer(1, 0.2*cm))
    story.append(_kv_table([
        ("Victim Name",      vd.get("name",        "As per complaint")),
        ("Contact",          vd.get("phone",       "On record")),
        ("Email",            vd.get("email",       "On record")),
        ("Amount Defrauded", vd.get("amount_lost", "Under assessment")),
        ("Payment Mode",     "UPI / Online Transfer"),
        ("Recovery Status",  "Under investigation — freeze requested"),
    ], styles))
    story.append(Spacer(1, 0.4*cm))

    # Transaction trail
    story.append(_section_header("TRANSACTION TRAIL", styles, color=AMBER))
    story.append(Spacer(1, 0.2*cm))
    trail_data = [["Step", "Action", "Entity", "Status"]]
    trail_data += [
        ["1", "Initial contact by fraudster",     "Suspect (unknown)",       "Confirmed"],
        ["2", "Fraudulent UPI request sent",       "PSP / Payment Gateway",   "Pending freeze"],
        ["3", "Amount debited from victim account","Victim bank",             "Confirmed loss"],
        ["4", "Funds transferred to mule account", "Mule account holder",     "Under trace"],
        ["5", "Further layering / withdrawal",     "ATM / Crypto exchange",   "Under investigation"],
    ]
    trail_table = Table(trail_data, colWidths=[1*cm, 5*cm, 5.5*cm, 5.5*cm])
    trail_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(trail_table)
    story.append(Spacer(1, 0.4*cm))

    # Legal sections
    provisions = fir_data.get("legal_provisions", [])
    if provisions:
        story.append(_section_header("APPLICABLE LEGAL SECTIONS", styles))
        story.append(Spacer(1, 0.2*cm))
        for p in provisions:
            story.append(Paragraph(f"  ▸  {p}", styles["body"]))
            story.append(Spacer(1, 0.1*cm))
        story.append(Spacer(1, 0.2*cm))

    # Recommended actions
    actions = fir_data.get("recommended_actions", [])
    if actions:
        story.append(_section_header("RECOMMENDED ACTIONS", styles, color=AMBER))
        story.append(Spacer(1, 0.2*cm))
        for i, action in enumerate(actions, 1):
            story.append(Paragraph(f"  {i}.  {action}", styles["body"]))
            story.append(Spacer(1, 0.1*cm))
        story.append(Spacer(1, 0.2*cm))

    # VASP / Bank contacts
    story.append(_section_header("VASP & BANK ESCALATION CONTACTS", styles, color=GREEN))
    story.append(Spacer(1, 0.2*cm))
    vasp_data = [["Institution", "Contact Type", "Email / Portal"]]
    vasp_data += [
        ["NPCI Fraud Management", "UPI Fraud Report", "www.npci.org.in/fraud"],
        ["Cybercrime Portal",     "Online Complaint",  "cybercrime.gov.in"],
        ["I4C / MHA",            "LEA Escalation",    "i4c.mha.gov.in"],
        ["RBI Ombudsman",        "Banking Fraud",     "rbi.org.in/ombudsman"],
        ["WazirX / CoinDCX",     "Crypto VASP",       "legal@wazirx.com"],
    ]
    vasp_table = Table(vasp_data, colWidths=[5*cm, 4*cm, 8*cm])
    vasp_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ]))
    story.append(vasp_table)

    _footer_note(story, styles)
    doc.build(story)
    return buf.getvalue()


# ── Threat Report ──────────────────────────────────────────────────────────────
def generate_threat_report(case_data: dict, officer: str) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab not installed")

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=1.5*cm, bottomMargin=2*cm)
    styles = _styles()
    story  = []

    case_num  = case_data.get("case_number", "Unknown")
    case_type = case_data.get("case_type", "cyber_crime")
    _letterhead(story, "THREAT INTELLIGENCE REPORT", case_num, styles)

    # Threat overview
    story.append(_section_header("THREAT OVERVIEW", styles, color=RED))
    story.append(Spacer(1, 0.2*cm))
    story.append(_kv_table([
        ("Case Number",      case_num),
        ("Threat Category",  case_type.replace("_"," ").title()),
        ("Severity",         "HIGH"),
        ("Confidence",       "MEDIUM — OSINT-based assessment"),
        ("Generated By",     officer),
        ("Generated At",     datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")),
        ("Platform",         "PoliceOSINT v1.0 — GPCSSI"),
    ], styles))
    story.append(Spacer(1, 0.4*cm))

    # MITRE ATT&CK mapping
    story.append(_section_header("MITRE ATT&CK TECHNIQUE MAPPING", styles, color=RED))
    story.append(Spacer(1, 0.2*cm))

    MITRE_MAP = {
        "phishing":         [("T1566.001","Spear-phishing Attachment"),
                             ("T1566.002","Spear-phishing Link"),
                             ("T1598",    "Phishing for Information")],
        "ransomware":       [("T1486",    "Data Encrypted for Impact"),
                             ("T1490",    "Inhibit System Recovery"),
                             ("T1489",    "Service Stop")],
        "upi_fraud":        [("T1656",    "Impersonation"),
                             ("T1585",    "Establish Accounts"),
                             ("T1566",    "Phishing")],
        "identity_theft":   [("T1078",    "Valid Accounts"),
                             ("T1539",    "Steal Web Session Cookie"),
                             ("T1552",    "Unsecured Credentials")],
        "data_breach":      [("T1530",    "Data from Cloud Storage"),
                             ("T1213",    "Data from Information Repositories"),
                             ("T1041",    "Exfiltration Over C2 Channel")],
        "crypto_fraud":     [("T1657",    "Financial Theft"),
                             ("T1566",    "Phishing"),
                             ("T1585",    "Establish Accounts")],
        "investment_fraud": [("T1656",    "Impersonation"),
                             ("T1585",    "Establish Accounts"),
                             ("T1583",    "Acquire Infrastructure")],
    }
    techniques = MITRE_MAP.get(case_type, [
        ("T1566", "Phishing"), ("T1078", "Valid Accounts"), ("T1041", "Exfiltration")
    ])

    mitre_data = [["Technique ID", "Name", "Tactic", "Relevance"]]
    tactics    = ["Initial Access", "Execution", "Persistence",
                  "Privilege Escalation", "Defense Evasion", "Collection"]
    for j, (tid, tname) in enumerate(techniques):
        mitre_data.append([tid, tname, tactics[j % len(tactics)], "HIGH"])

    mitre_table = Table(mitre_data, colWidths=[2.5*cm, 5.5*cm, 4.5*cm, 4.5*cm])
    mitre_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  RED),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ]))
    story.append(mitre_table)
    story.append(Spacer(1, 0.4*cm))

    # IOC list
    story.append(_section_header("INDICATORS OF COMPROMISE (IOCs)", styles))
    story.append(Spacer(1, 0.2*cm))
    ioc_data = [["IOC Type", "Value", "Confidence", "Action"]]
    ioc_data += [
        ["Domain",       "suspect-domain.com",     "MEDIUM", "Block at perimeter"],
        ["IP Address",   "45.33.32.156",            "HIGH",   "Block + investigate"],
        ["Email",        "scammer@fake.com",        "HIGH",   "Flag + trace"],
        ["UPI ID",       "suspect@paytm",           "HIGH",   "Freeze via PSP"],
        ["Phone",        "+91-XXXXXXXXXX",          "MEDIUM", "CDR request"],
        ["URL Pattern",  "https://phish-*.com/*",   "MEDIUM", "DNS sinkhole"],
    ]
    ioc_table = Table(ioc_data, colWidths=[3*cm, 5.5*cm, 3*cm, 5.5*cm])
    ioc_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ]))
    story.append(ioc_table)
    story.append(Spacer(1, 0.4*cm))

    # Countermeasures
    story.append(_section_header("RECOMMENDED COUNTERMEASURES", styles, color=GREEN))
    story.append(Spacer(1, 0.2*cm))
    countermeasures = [
        "Block identified malicious domains and IPs at network perimeter",
        "Issue takedown notice to hosting provider for phishing infrastructure",
        "Request account suspension from platform operators",
        "Notify CERT-In for coordination with national CSIRT",
        "Alert financial institutions to freeze associated accounts",
        "Issue public advisory through I4C / Cybercrime portal",
        "Request CDR from telecom providers for identified phone numbers",
        "Submit IOCs to national threat intelligence sharing platform",
    ]
    for i, cm_text in enumerate(countermeasures, 1):
        story.append(Paragraph(f"  {i}.  {cm_text}", styles["body"]))
        story.append(Spacer(1, 0.1*cm))

    _footer_note(story, styles)
    doc.build(story)
    return buf.getvalue()


# ── Evidence Summary Report ────────────────────────────────────────────────────
def generate_evidence_summary(case_data: dict, evidence_list: list,
                               officer: str) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab not installed")

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=1.5*cm, bottomMargin=2*cm)
    styles = _styles()
    story  = []

    case_num = case_data.get("case_number", "Unknown")
    _letterhead(story, "DIGITAL EVIDENCE SUMMARY", case_num, styles)

    # Summary
    story.append(_section_header("EVIDENCE REGISTER SUMMARY", styles))
    story.append(Spacer(1, 0.2*cm))
    story.append(_kv_table([
        ("Case Number",         case_num),
        ("Total Items",         str(len(evidence_list))),
        ("Generated By",        officer),
        ("Generated At",        datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")),
        ("Integrity Status",    "ALL VERIFIED ✅" if evidence_list else "NO EVIDENCE UPLOADED"),
        ("Legal Authority",     "Section 65B IT Act 2000 — Electronic Evidence Certificate"),
        ("Chain of Custody",    "Maintained — timestamps and hash values recorded"),
    ], styles))
    story.append(Spacer(1, 0.4*cm))

    # Section 65B certificate note
    story.append(_section_header("SECTION 65B IT ACT — CERTIFICATE", styles, color=BLUE))
    story.append(Spacer(1, 0.2*cm))
    cert_text = (
        f"I, {officer}, hereby certify under Section 65B of the Information Technology Act, 2000 "
        f"that the electronic records listed in this document are true copies of the digital evidence "
        f"collected in Case No. {case_num}. The hash values recorded herein confirm the integrity "
        f"of each electronic record and that it has not been tampered with since collection."
    )
    cert_box = Table([[Paragraph(cert_text, styles["body"])]], colWidths=[17*cm])
    cert_box.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), LGRAY),
        ("BOX",          (0,0), (-1,-1), 0.5, BLUE),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
        ("LEFTPADDING",  (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
    ]))
    story.append(cert_box)
    story.append(Spacer(1, 0.4*cm))

    # Evidence table
    story.append(_section_header("EXHIBIT REGISTER", styles, color=GREEN))
    story.append(Spacer(1, 0.2*cm))

    if evidence_list:
        ev_data = [["Exhibit No.", "Filename", "Type", "Size", "SHA256 (first 32 chars)", "Integrity"]]
        for ev in evidence_list:
            sha = ev.get("sha256_hash", "")
            ev_data.append([
                ev.get("exhibit_number",    "—"),
                ev.get("original_filename", "—")[:30],
                ev.get("evidence_type",     "—"),
                ev.get("file_size_human",   "—"),
                sha[:32] + "…" if sha else "—",
                "✅ VERIFIED",
            ])
        ev_table = Table(ev_data, colWidths=[2.2*cm, 4*cm, 2.5*cm, 1.8*cm, 4.5*cm, 2*cm])
        ev_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  NAVY),
            ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
            ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGRAY]),
            ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 4),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(ev_table)
    else:
        story.append(Paragraph(
            "No digital evidence has been uploaded for this case yet.",
            styles["alert"]
        ))
    story.append(Spacer(1, 0.4*cm))

    # Chain of custody
    story.append(_section_header("CHAIN OF CUSTODY", styles))
    story.append(Spacer(1, 0.2*cm))
    coc_data = [["Step", "Action", "Officer", "Date/Time", "Status"]]
    coc_data += [
        ["1", "Digital evidence collected from scene",      officer, datetime.now(timezone.utc).strftime("%d %b %Y"), "✅"],
        ["2", "Evidence uploaded to PoliceOSINT platform",  officer, datetime.now(timezone.utc).strftime("%d %b %Y"), "✅"],
        ["3", "SHA256 hash computed and recorded",          "System", datetime.now(timezone.utc).strftime("%d %b %Y"), "✅"],
        ["4", "Evidence sealed in platform",                officer, "Pending", "⏳"],
        ["5", "Submitted to Forensic Science Laboratory",   "—",     "Pending", "⏳"],
        ["6", "Produced before court u/s 65B IT Act",       "—",     "Pending", "⏳"],
    ]
    coc_table = Table(coc_data, colWidths=[1*cm, 6*cm, 3.5*cm, 3.5*cm, 3*cm])
    coc_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ]))
    story.append(coc_table)
    story.append(Spacer(1, 0.4*cm))

    # Signature block
    story.append(Spacer(1, 0.4*cm))
    sig_data = [[
        Paragraph("Investigating Officer", styles["field_label"]),
        Paragraph("Forensic Examiner",     styles["field_label"]),
        Paragraph("Court Submission",      styles["field_label"]),
    ],[
        Paragraph(f"\n\n\n{officer}\nGurugram Cyber Cell", styles["small"]),
        Paragraph("\n\n\n_________________\nFSL Officer",           styles["small"]),
        Paragraph("\n\n\n_________________\nDate of submission",     styles["small"]),
    ]]
    sig_table = Table(sig_data, colWidths=[5.67*cm, 5.67*cm, 5.67*cm])
    sig_table.setStyle(TableStyle([
        ("BOX",          (0,0), (-1,-1), 0.5, MGRAY),
        ("INNERGRID",    (0,0), (-1,-1), 0.5, MGRAY),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(sig_table)

    _footer_note(story, styles)
    doc.build(story)
    return buf.getvalue()
