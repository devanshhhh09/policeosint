import enum
from sqlalchemy import Column, String, Boolean, Enum, DateTime
from sqlalchemy.orm import relationship
from app.db.models.base import BaseModel

class UserRole(str, enum.Enum):
    SUPER_ADMIN   = "super_admin"
    COMMISSIONER  = "commissioner"
    SP            = "sp"
    INSPECTOR     = "inspector"
    SUB_INSPECTOR = "sub_inspector"
    CONSTABLE     = "constable"
    ANALYST       = "analyst"
    TRAINEE       = "trainee"

class UserStatus(str, enum.Enum):
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    SUSPENDED = "suspended"

class User(BaseModel):
    __tablename__ = "users"
    badge_number    = Column(String(50),  unique=True, nullable=False, index=True)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    full_name       = Column(String(255), nullable=False)
    phone           = Column(String(20),  nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(Enum(UserRole),   default=UserRole.ANALYST,     nullable=False)
    status          = Column(Enum(UserStatus), default=UserStatus.ACTIVE,    nullable=False)
    is_verified     = Column(Boolean, default=False)
    station_name    = Column(String(255), nullable=True)
    district        = Column(String(100), nullable=True)
    state           = Column(String(100), default="Haryana")
    designation     = Column(String(100), nullable=True)
    last_login      = Column(DateTime(timezone=True), nullable=True)
    failed_attempts = Column(String(10), default="0")
    avatar_url      = Column(String(500), nullable=True)

    cases_created  = relationship("Case", back_populates="created_by", foreign_keys="Case.created_by_id")
    audit_logs     = relationship("AuditLog", back_populates="user")
    investigations = relationship("Investigation", back_populates="investigator")
