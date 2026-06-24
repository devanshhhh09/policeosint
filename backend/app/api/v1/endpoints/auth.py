from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone
from uuid import UUID
from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token,
    create_refresh_token, decode_token, hash_password
)
from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.db.models.user import User, UserStatus
from app.db.models.audit import AuditLog, AuditAction
from app.schemas.auth import (
    LoginRequest, TokenResponse,
    RefreshRequest, ChangePasswordRequest
)
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.badge_number == credentials.badge_number)
    )
    user = result.scalar_one_or_none()
    ip = request.client.host if request.client else "unknown"

    if not user or not verify_password(credentials.password, user.hashed_password):
        db.add(AuditLog(
            user_id=user.id if user else None,
            action=AuditAction.LOGIN_FAILED,
            resource="auth",
            description=f"Failed login: {credentials.badge_number}",
            ip_address=ip,
            status="failure",
        ))
        await db.commit()
        raise UnauthorizedError("Invalid badge number or password")

    if user.status != UserStatus.ACTIVE:
        raise UnauthorizedError(f"Account is {user.status}")

    await db.execute(
        update(User).where(User.id == user.id)
        .values(failed_attempts="0", last_login=datetime.now(timezone.utc))
    )
    token_data = {
        "sub": str(user.id),
        "role": user.role,
        "badge": user.badge_number,
    }
    db.add(AuditLog(
        user_id=user.id,
        action=AuditAction.LOGIN,
        resource="auth",
        description=f"Login from {ip}",
        ip_address=ip,
        status="success",
    ))
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id":           str(user.id),
            "badge_number": user.badge_number,
            "full_name":    user.full_name,
            "email":        user.email,
            "role":         user.role,
            "station_name": user.station_name,
            "district":     user.district,
            "avatar_url":   user.avatar_url,
        },
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid refresh token")
    result = await db.execute(select(User).where(User.id == UUID(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user or user.status != UserStatus.ACTIVE:
        raise UnauthorizedError("User not found or inactive")
    token_data = {"sub": str(user.id), "role": user.role, "badge": user.badge_number}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={"id": str(user.id), "badge_number": user.badge_number, "role": user.role},
    )

@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.LOGOUT,
        resource="auth",
        description="Logged out",
        ip_address=request.client.host if request.client else "unknown",
        status="success",
    ))
    await db.commit()
    return {"message": "Logged out successfully"}

@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id":           str(current_user.id),
        "badge_number": current_user.badge_number,
        "full_name":    current_user.full_name,
        "email":        current_user.email,
        "role":         current_user.role,
        "status":       current_user.status,
        "station_name": current_user.station_name,
        "district":     current_user.district,
        "designation":  current_user.designation,
        "is_verified":  current_user.is_verified,
        "last_login":   current_user.last_login,
        "created_at":   current_user.created_at,
    }

@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise UnauthorizedError("Current password is incorrect")
    await db.execute(
        update(User).where(User.id == current_user.id)
        .values(hashed_password=hash_password(body.new_password))
    )
    await db.commit()
    return {"message": "Password changed successfully"}
