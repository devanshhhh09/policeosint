from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from uuid import UUID
from datetime import datetime
import random
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.db.models.case import Case, CaseNote
from app.db.models.user import User
from app.db.models.audit import AuditLog, AuditAction
from app.schemas.case import (
    CaseCreate, CaseUpdate, CaseNoteCreate,
    CaseResponse, CaseListResponse
)
from app.api.deps import get_current_user, require_perm

router = APIRouter()

def gen_case_number():
    return f"CYB/{datetime.now().year}/{random.randint(1000,9999)}"

@router.get("/", response_model=CaseListResponse)
async def list_cases(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, le=100),
    status: str = Query(None),
    case_type: str = Query(None),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("case:read")),
):
    q = select(Case)
    if status:    q = q.where(Case.status == status)
    if case_type: q = q.where(Case.case_type == case_type)
    if search:
        q = q.where(or_(
            Case.title.ilike(f"%{search}%"),
            Case.case_number.ilike(f"%{search}%"),
            Case.victim_name.ilike(f"%{search}%"),
        ))
    if current_user.role in ["constable", "trainee", "sub_inspector"]:
        q = q.where(or_(
            Case.created_by_id == current_user.id,
            Case.assigned_to_id == current_user.id,
        ))
    q = q.order_by(Case.created_at.desc())
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    result = await db.execute(q.offset((page - 1) * per_page).limit(per_page))
    return CaseListResponse(
        cases=[CaseResponse.model_validate(c) for c in result.scalars().all()],
        total=total, page=page, per_page=per_page,
    )

@router.post("/", response_model=CaseResponse, status_code=201)
async def create_case(
    data: CaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("case:create")),
):
    case = Case(**data.model_dump(), case_number=gen_case_number(), created_by_id=current_user.id)
    db.add(case)
    db.add(AuditLog(
        user_id=current_user.id, action=AuditAction.CASE_CREATE,
        resource="case", description=f"Created {case.case_number}", status="success",
    ))
    await db.commit()
    await db.refresh(case)
    return CaseResponse.model_validate(case)

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("case:read")),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case: raise NotFoundError("Case", str(case_id))
    return CaseResponse.model_validate(case)

@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: UUID,
    data: CaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("case:update")),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case: raise NotFoundError("Case", str(case_id))
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(case, k, v)
    db.add(AuditLog(
        user_id=current_user.id, action=AuditAction.CASE_UPDATE,
        resource="case", resource_id=str(case_id),
        description=f"Updated {case.case_number}", status="success",
    ))
    await db.commit()
    await db.refresh(case)
    return CaseResponse.model_validate(case)

@router.delete("/{case_id}", status_code=204)
async def delete_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("case:delete")),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case: raise NotFoundError("Case", str(case_id))
    await db.delete(case)
    await db.commit()

@router.post("/{case_id}/notes", status_code=201)
async def add_note(
    case_id: UUID,
    data: CaseNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("case:read")),
):
    note = CaseNote(case_id=case_id, author_id=current_user.id, **data.model_dump())
    db.add(note)
    await db.commit()
    return {"message": "Note added", "id": str(note.id)}

@router.get("/{case_id}/notes")
async def get_notes(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_perm("case:read")),
):
    result = await db.execute(
        select(CaseNote)
        .where(CaseNote.case_id == case_id)
        .order_by(CaseNote.created_at.desc())
    )
    notes = result.scalars().all()
    return [
        {
            "id":         str(n.id),
            "content":    n.content,
            "note_type":  n.note_type,
            "is_private": n.is_private,
            "author_id":  str(n.author_id),
            "created_at": n.created_at,
        }
        for n in notes
        if not n.is_private or str(n.author_id) == str(current_user.id)
    ]
