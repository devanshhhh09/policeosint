from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.models.case import Case
from app.db.models.investigation import Investigation, InvestigationResult
from app.db.models.evidence import Evidence
from app.services.pdf_service import (
    generate_fir_support,
    generate_intelligence,
    generate_fraud,
    generate_threat,
    generate_suspect_profile,
)

router = APIRouter()

REPORT_GENERATORS = {
    "fir_support":     generate_fir_support,
    "intelligence":    generate_intelligence,
    "fraud":           generate_fraud,
    "threat":          generate_threat,
    "suspect_profile": generate_suspect_profile,
}


async def _load_case(case_id: UUID, db: AsyncSession) -> Case:
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


async def _load_investigations(case_id: UUID, db: AsyncSession) -> list:
    result = await db.execute(
        select(Investigation)
        .where(Investigation.case_id == case_id)
        .order_by(Investigation.created_at.desc())
    )
    investigations = result.scalars().all()
    for inv in investigations:
        res = await db.execute(
            select(InvestigationResult)
            .where(InvestigationResult.investigation_id == inv.id)
        )
        inv.results = res.scalars().all()
    return investigations


async def _load_evidence(case_id: UUID, db: AsyncSession) -> list:
    result = await db.execute(
        select(Evidence).where(Evidence.case_id == case_id)
    )
    return result.scalars().all()


# IMPORTANT: specific routes before parameterised routes
@router.get("/available/{case_id}")
async def list_available_reports(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case      = await _load_case(case_id, db)
    inv_count = len(await _load_investigations(case_id, db))
    ev_count  = len(await _load_evidence(case_id, db))
    return {
        "case_number": case.case_number,
        "reports": [
            {"type": "fir_support",     "label": "FIR Support Report",    "ready": True},
            {"type": "intelligence",    "label": "Intelligence Report",    "ready": inv_count > 0},
            {"type": "fraud",           "label": "Fraud Investigation",    "ready": True},
            {"type": "threat",          "label": "Threat Report",          "ready": inv_count > 0},
            {"type": "suspect_profile", "label": "Suspect Profile",        "ready": inv_count > 0},
        ],
        "investigation_count": inv_count,
        "evidence_count":      ev_count,
    }


@router.get("/download/{case_id}/{report_type}")
async def download_pdf_report(
    case_id: UUID,
    report_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if report_type not in REPORT_GENERATORS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown report type. Choose from: {', '.join(REPORT_GENERATORS)}"
        )

    case           = await _load_case(case_id, db)
    investigations = await _load_investigations(case_id, db)
    evidence_list  = await _load_evidence(case_id, db)

    try:
        generator = REPORT_GENERATORS[report_type]
        if report_type == "fir_support":
            pdf = generator(case, investigations, evidence_list, current_user)
        else:
            pdf = generator(case, investigations, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    filename = f"PoliceOSINT_{report_type}_{case.case_number.replace('/', '_')}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
