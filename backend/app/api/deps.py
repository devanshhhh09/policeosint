from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.core.database import get_db
from app.core.security import decode_token, check_permission
from app.db.models.user import User, UserStatus
from app.core.exceptions import UnauthorizedError, ForbiddenError

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    try:
        user_id = UUID(payload.get("sub", ""))
    except Exception:
        raise UnauthorizedError("Invalid token payload")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found")
    if user.status != UserStatus.ACTIVE:
        raise UnauthorizedError(f"Account is {user.status}")
    return user

def require_perm(permission: str):
    async def check(current_user: User = Depends(get_current_user)) -> User:
        if not check_permission(current_user.role, permission):
            raise ForbiddenError(f"Permission denied: {permission}")
        return current_user
    return check
