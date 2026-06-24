from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.db.models.case import CaseStatus, CasePriority, CaseType

class CaseCreate(BaseModel):
    title: str
    case_type: CaseType
    priority: CasePriority = CasePriority.MEDIUM
    description: Optional[str] = None
    fir_number: Optional[str] = None
    amount_lost: Optional[str] = None
    victim_name: Optional[str] = None
    victim_phone: Optional[str] = None
    victim_email: Optional[str] = None
    incident_location: Optional[str] = None
    ipc_sections: List[str] = []
    tags: List[str] = []
    suspect_info: Optional[dict] = None

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    priority: Optional[CasePriority] = None
    fir_number: Optional[str] = None
    amount_lost: Optional[str] = None
    amount_recovered: Optional[str] = None
    victim_name: Optional[str] = None
    victim_phone: Optional[str] = None
    incident_location: Optional[str] = None
    ipc_sections: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_fir_filed: Optional[bool] = None
    court_case_number: Optional[str] = None

class CaseNoteCreate(BaseModel):
    content: str
    note_type: str = "general"
    is_private: bool = False

class CaseResponse(BaseModel):
    id: UUID
    case_number: str
    fir_number: Optional[str]
    title: str
    case_type: CaseType
    status: CaseStatus
    priority: CasePriority
    amount_lost: Optional[str]
    victim_name: Optional[str]
    victim_phone: Optional[str]
    incident_location: Optional[str]
    ipc_sections: List[str]
    tags: List[str]
    is_fir_filed: bool
    created_at: datetime
    updated_at: datetime
    created_by_id: UUID
    assigned_to_id: Optional[UUID]
    model_config = {"from_attributes": True}

class CaseListResponse(BaseModel):
    cases: List[CaseResponse]
    total: int
    page: int
    per_page: int
