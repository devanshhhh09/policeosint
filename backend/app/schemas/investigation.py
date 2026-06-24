from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.db.models.investigation import InvestigationType, InvestigationStatus

class InvestigationCreate(BaseModel):
    investigation_type: InvestigationType
    query: str
    query_type: Optional[str] = None
    case_id: Optional[UUID] = None

class InvestigationResponse(BaseModel):
    id: UUID
    investigation_type: InvestigationType
    query: str
    query_type: Optional[str]
    status: InvestigationStatus
    progress: float
    risk_score: Optional[float]
    summary: Optional[str]
    sources_queried: List[str]
    created_at: datetime
    updated_at: datetime
    case_id: Optional[UUID]
    investigator_id: UUID
    model_config = {"from_attributes": True}
