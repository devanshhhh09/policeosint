import enum
from sqlalchemy import Column, String, Text, Enum, ForeignKey, Boolean, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.models.base import BaseModel

class InvestigationType(str, enum.Enum):
    IDENTITY     = "identity"
    SOCIAL_MEDIA = "social_media"
    DOMAIN       = "domain"
    IP           = "ip"
    UPI_FRAUD    = "upi_fraud"
    CRYPTO       = "crypto"
    THREAT       = "threat"
    DARK_WEB     = "dark_web"
    GEOINT       = "geoint"
    MEDIA        = "media"

class InvestigationStatus(str, enum.Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    PARTIAL   = "partial"

class Investigation(BaseModel):
    __tablename__ = "investigations"
    case_id            = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)
    investigator_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    investigation_type = Column(Enum(InvestigationType),  nullable=False)
    query              = Column(String(1000), nullable=False)
    query_type         = Column(String(100),  nullable=True)
    status             = Column(Enum(InvestigationStatus), default=InvestigationStatus.PENDING)
    progress           = Column(Float, default=0.0)
    risk_score         = Column(Float, nullable=True)
    summary            = Column(Text,  nullable=True)
    sources_queried    = Column(JSON,  default=list)
    error_message      = Column(Text,  nullable=True)
    celery_task_id     = Column(String(255), nullable=True)
    case         = relationship("Case", back_populates="investigations")
    investigator = relationship("User", back_populates="investigations")
    results      = relationship("InvestigationResult", back_populates="investigation",
                                cascade="all, delete-orphan")

class InvestigationResult(BaseModel):
    __tablename__ = "investigation_results"
    investigation_id  = Column(UUID(as_uuid=True), ForeignKey("investigations.id"), nullable=False)
    source_name       = Column(String(100), nullable=False)
    parsed_data       = Column(JSON, nullable=True)
    raw_data          = Column(Text, nullable=True)
    is_suspicious     = Column(Boolean, default=False)
    risk_contribution = Column(Float,   default=0.0)
    investigation = relationship("Investigation", back_populates="results")
