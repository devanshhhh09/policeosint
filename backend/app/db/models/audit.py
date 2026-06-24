import enum
from sqlalchemy import Column, String, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.models.base import BaseModel

class AuditAction(str, enum.Enum):
    LOGIN              = "login"
    LOGOUT             = "logout"
    LOGIN_FAILED       = "login_failed"
    CASE_CREATE        = "case_create"
    CASE_UPDATE        = "case_update"
    CASE_DELETE        = "case_delete"
    EVIDENCE_UPLOAD    = "evidence_upload"
    INVESTIGATION_RUN  = "investigation_run"
    REPORT_GENERATE    = "report_generate"
    USER_CREATE        = "user_create"
    PERMISSION_DENIED  = "permission_denied"

class AuditLog(BaseModel):
    __tablename__ = "audit_logs"
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action      = Column(Enum(AuditAction), nullable=False, index=True)
    resource    = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    description = Column(Text,        nullable=True)
    ip_address  = Column(String(45),  nullable=True)
    user_agent  = Column(String(500), nullable=True)
    status      = Column(String(20),  default="success")
    user = relationship("User", back_populates="audit_logs")
