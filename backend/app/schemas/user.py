from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.db.models.user import UserRole, UserStatus

class UserCreate(BaseModel):
    badge_number: str
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.ANALYST
    station_name: Optional[str] = None
    district: Optional[str] = None
    designation: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Minimum 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Need at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Need at least one digit")
        return v

class UserResponse(BaseModel):
    id: UUID
    badge_number: str
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    is_verified: bool
    station_name: Optional[str]
    district: Optional[str]
    designation: Optional[str]
    last_login: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}
