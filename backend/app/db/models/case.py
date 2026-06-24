import enum
from sqlalchemy import Column, String, Text, Enum, ForeignKey, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.models.base import BaseModel

class CaseStatus(str, enum.Enum):
    DRAFT        = "draft"
    OPEN         = "open"
    ACTIVE       = "active"
    UNDER_REVIEW = "under_review"
    ESCALATED    = "escalated"
    CLOSED       = "closed"
    ARCHIVED     = "archived"

class CasePriority(str, enum.Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"

class CaseType(str, enum.Enum):
    UPI_FRAUD        = "upi_fraud"
    CYBER_CRIME      = "cyber_crime"
    PHISHING         = "phishing"
    RANSOMWARE       = "ransomware"
    IDENTITY_THEFT   = "identity_theft"
    DATA_BREACH      = "data_breach"
    INVESTMENT_FRAUD = "investment_fraud"
    LOAN_SCAM        = "loan_scam"
    ROMANCE_SCAM     = "romance_scam"
    CRYPTO_FRAUD     = "crypto_fraud"
    DARK_WEB         = "dark_web"
    OTHER            = "other"

class Case(BaseModel):
    __tablename__ = "cases"
    case_number       = Column(String(50),  unique=True, nullable=False, index=True)
    fir_number        = Column(String(50),  unique=True, nullable=True,  index=True)
    title             = Column(String(500), nullable=False)
    description       = Column(Text,        nullable=True)
    case_type         = Column(Enum(CaseType),     nullable=False)
    status            = Column(Enum(CaseStatus),   default=CaseStatus.OPEN,     nullable=False)
    priority          = Column(Enum(CasePriority), default=CasePriority.MEDIUM, nullable=False)
    created_by_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    amount_lost       = Column(String(50),  nullable=True)
    amount_recovered  = Column(String(50),  nullable=True)
    victim_name       = Column(String(255), nullable=True)
    victim_phone      = Column(String(20),  nullable=True)
    victim_email      = Column(String(255), nullable=True)
    suspect_info      = Column(JSON, nullable=True)
    incident_location = Column(String(500), nullable=True)
    ipc_sections      = Column(JSON, default=list)
    tags              = Column(JSON, default=list)
    is_fir_filed      = Column(Boolean, default=False)
    court_case_number = Column(String(100), nullable=True)

    created_by   = relationship("User", back_populates="cases_created", foreign_keys=[created_by_id])
    assigned_to  = relationship("User", foreign_keys=[assigned_to_id])
    notes        = relationship("CaseNote",       back_populates="case", cascade="all, delete-orphan")
    evidence     = relationship("Evidence",        back_populates="case", cascade="all, delete-orphan")
    investigations = relationship("Investigation", back_populates="case")
    assignments  = relationship("CaseAssignment", back_populates="case")

class CaseNote(BaseModel):
    __tablename__ = "case_notes"
    case_id    = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    author_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content    = Column(Text,       nullable=False)
    note_type  = Column(String(50), default="general")
    is_private = Column(Boolean,    default=False)
    case   = relationship("Case", back_populates="notes")
    author = relationship("User")

class CaseAssignment(BaseModel):
    __tablename__ = "case_assignments"
    case_id     = Column(UUID(as_uuid=True), ForeignKey("cases.id"),  nullable=False)
    officer_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"),  nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"),  nullable=False)
    is_lead     = Column(Boolean, default=False)
    case    = relationship("Case", back_populates="assignments")
    officer = relationship("User", foreign_keys=[officer_id])
