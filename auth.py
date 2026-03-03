"""Authentication and role-based authorization helpers."""

from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from config import (
    JWT_EXPIRE_HOURS,
    JWT_SECRET,
    NORMAL_USER_PASSWORD,
    NORMAL_USER_USERNAME,
    SUPER_ADMIN_PASSWORD,
    SUPER_ADMIN_USERNAME,
)

Role = Literal["user", "super_admin"]

security = HTTPBearer(auto_error=False)


class AuthUser(BaseModel):
    username: str
    role: Role
    expires_at: datetime


def _credentials_map() -> dict[str, tuple[str, Role]]:
    return {
        NORMAL_USER_USERNAME: (NORMAL_USER_PASSWORD, "user"),
        SUPER_ADMIN_USERNAME: (SUPER_ADMIN_PASSWORD, "super_admin"),
    }


def authenticate(username: str, password: str) -> AuthUser | None:
    record = _credentials_map().get(username)
    if not record:
        return None
    expected_password, role = record
    if password != expected_password:
        return None

    expires_at = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    return AuthUser(username=username, role=role, expires_at=expires_at)


def create_access_token(user: AuthUser) -> str:
    payload = {
        "sub": user.username,
        "role": user.role,
        "exp": int(user.expires_at.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> AuthUser:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    username = payload.get("sub")
    role = payload.get("role")
    exp = payload.get("exp")

    if not username or role not in {"user", "super_admin"} or not exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    return AuthUser(username=username, role=role, expires_at=expires_at)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser:
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    return decode_token(creds.credentials)


def require_super_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return user
