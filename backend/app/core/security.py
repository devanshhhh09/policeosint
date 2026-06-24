from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

PERMISSIONS = {
    "case:create":     ["inspector","sub_inspector","sp","commissioner","super_admin"],
    "case:read":       ["constable","analyst","trainee","inspector","sub_inspector","sp","commissioner","super_admin"],
    "case:update":     ["inspector","sp","commissioner","super_admin"],
    "case:delete":     ["sp","commissioner","super_admin"],
    "case:assign":     ["inspector","sp","commissioner","super_admin"],
    "evidence:upload": ["constable","inspector","sub_inspector","sp","commissioner","super_admin"],
    "investigate:run": ["analyst","inspector","sub_inspector","sp","commissioner","super_admin"],
    "report:generate": ["inspector","sp","commissioner","super_admin"],
    "report:view":     ["constable","analyst","inspector","sub_inspector","sp","commissioner","super_admin"],
    "user:manage":     ["sp","commissioner","super_admin"],
    "audit:view":      ["commissioner","super_admin"],
}

def hash_password(p: str) -> str:
    return pwd_context.hash(p)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def check_permission(role: str, permission: str) -> bool:
    return role in PERMISSIONS.get(permission, [])
