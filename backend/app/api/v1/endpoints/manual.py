"""Police user manual endpoint — Phase 6"""
from fastapi import APIRouter, Depends
from app.db.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

MANUAL = {
    "title": "PoliceOSINT — Officer User Manual",
    "version": "1.0",
    "platform": "GPCSSI · Gurugram Cyber Cell",
    "sections": [
        {
            "id": "1",
            "title": "Getting Started",
            "content": "Login with your badge number and password. Your role determines what features you can access. Inspectors can run investigations and manage cases. Analysts can run OSINT tools. Trainees have read-only access.",
            "steps": [
                "Go to http://localhost:3000",
                "Enter your badge number (e.g. GGN/CYB/2024/001)",
                "Enter your password",
                "Click Login — you will land on the Command Dashboard",
            ],
        },
        {
            "id": "2",
            "title": "Creating a Case",
            "content": "Every investigation should be linked to a case. Cases track all evidence, notes, investigations, and reports in one place.",
            "steps": [
                "Click Cases in the sidebar",
                "Click New Case button",
                "Fill in: Title, Case Type, Priority, Victim details, IPC sections",
                "Click Create Case — a case number CYB/YEAR/XXXX is auto-generated",
                "Add notes using the Notes tab",
            ],
        },
        {
            "id": "3",
            "title": "Running an Investigation",
            "content": "Use the Investigate menu to run OSINT against a suspect. All investigations are automatically saved and linked to cases.",
            "steps": [
                "Click the relevant module (Identity / IP / Domain / UPI etc.)",
                "Select the query type (email, username, phone etc.)",
                "Enter the target value",
                "Optionally link to a case number",
                "Click Investigate — results appear in 2-10 seconds",
                "Review risk score and source findings",
                "Click Save to case to link results",
            ],
        },
        {
            "id": "4",
            "title": "UPI Fraud Investigation",
            "content": "The UPI module is the flagship feature. It analyses UPI IDs for fraud patterns, detects mule accounts, and maps the money trail.",
            "steps": [
                "Go to Investigate → UPI Fraud",
                "Enter the suspect UPI ID (e.g. suspect@paytm)",
                "Review the fraud risk score (0-100)",
                "Check fraud patterns detected (KYC scam, Remote access etc.)",
                "View mule account indicators",
                "Go to UPI Cluster to see the full mule network",
                "Use recommended actions to freeze accounts and file notices",
            ],
        },
        {
            "id": "5",
            "title": "Generating FIR Support Report",
            "content": "Generate a court-ready FIR support document with all IPC sections, evidence checklist, and notice templates pre-filled.",
            "steps": [
                "Go to Reports in the sidebar",
                "Select your case from the dropdown",
                "Click Download PDF next to FIR Support Report",
                "The PDF includes: Case details, victim info, IPC sections, evidence checklist, notice templates, escalation, signature block",
                "Print and attach to your FIR filing",
            ],
        },
        {
            "id": "6",
            "title": "Uploading Evidence",
            "content": "Upload screenshots, documents, and logs. The platform automatically computes SHA256 and MD5 hashes for chain of custody.",
            "steps": [
                "Open a case → click Evidence tab",
                "Click Choose file",
                "Select screenshot, PDF, log file, or image",
                "SHA256 hash is computed automatically",
                "Exhibit number is assigned (EX-YYYYMMDD-HHMMSS)",
                "Click Verify to re-check integrity at any time",
            ],
        },
        {
            "id": "7",
            "title": "AI Copilot",
            "content": "The AI Copilot assists with FIR notes, evidence correlation, and legal section identification. Requires OpenAI API key or Ollama.",
            "steps": [
                "Go to AI Copilot in the sidebar",
                "Type your question or click a Quick Action",
                "Ask: Draft FIR notes for UPI fraud",
                "Ask: Explain Section 66D IT Act",
                "Ask: What are KYC scam indicators?",
                "Copy the response to your investigation notes",
            ],
        },
        {
            "id": "8",
            "title": "Entity Relationship Graph",
            "content": "Visualise connections between suspects, UPI IDs, wallets, domains, and social accounts in an interactive graph.",
            "steps": [
                "Go to Entity Graph in the sidebar",
                "Enter a suspect identifier (UPI ID, email, IP etc.)",
                "Select the entity type",
                "Click Build graph",
                "Click any node to see its connections and risk score",
                "Click Expand to go deeper into the network",
            ],
        },
        {
            "id": "9",
            "title": "Important Legal References",
            "content": "Key sections used in cyber crime FIRs.",
            "sections": [
                "Section 419 IPC — Cheating by personation",
                "Section 420 IPC — Cheating (financial fraud)",
                "Section 66C IT Act — Identity theft",
                "Section 66D IT Act — Cheating by personation using computer",
                "Section 66F IT Act — Cyber terrorism",
                "Section 43A IT Act — Data protection failure",
                "Section 91 CrPC — Notice to produce documents",
                "PMLA 2002 — Money laundering (for large amounts)",
            ],
        },
        {
            "id": "10",
            "title": "Emergency Contacts",
            "content": "Key contacts for cyber crime investigations.",
            "contacts": [
                {"name": "National Cyber Crime Helpline", "contact": "1930"},
                {"name": "Cybercrime.gov.in portal",      "contact": "https://cybercrime.gov.in"},
                {"name": "CERT-In",                       "contact": "https://cert-in.org.in"},
                {"name": "I4C (MHA)",                     "contact": "https://i4c.mha.gov.in"},
                {"name": "NPCI Fraud Reporting",          "contact": "https://www.npci.org.in"},
            ],
        },
    ],
}


@router.get("/")
async def get_manual(current_user: User = Depends(get_current_user)):
    return MANUAL
