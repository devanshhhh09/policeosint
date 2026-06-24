import enum
from sqlalchemy import Column, String, Text, Enum, ForeignKey, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.models.base import BaseModel

class EvidenceType(str, enum.Enum):
    SCREENSHOT  = "screenshot"
    DOCUMENT    = "document"
    IMAGE       = "image"
    VIDEO       = "video"
    AUDIO       = "audio"
    LOG_FILE    = "log_file"
    EMAIL       = "email"
    CHAT_LOG    = "chat_log"
    TRANSACTION = "transaction"
    OTHER       = "other"

class Evidence(BaseModel):
    __tablename__ = "evidence"
    case_id           = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    uploaded_by_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename          = Column(String(500),  nullable=False)
    original_filename = Column(String(500),  nullable=False)
    file_path         = Column(String(1000), nullable=False)
    file_size         = Column(BigInteger,   nullable=False)
    mime_type         = Column(String(200),  nullable=True)
    evidence_type     = Column(Enum(EvidenceType), nullable=False)
    sha256_hash       = Column(String(64),  nullable=False, index=True)
    md5_hash          = Column(String(32),  nullable=True)
    description       = Column(Text,        nullable=True)
    exhibit_number    = Column(String(100), nullable=True)
    is_sealed         = Column(Boolean,     default=False)
    exif_data         = Column(Text,        nullable=True)
    case        = relationship("Case", back_populates="evidence")
    uploaded_by = relationship("User")
