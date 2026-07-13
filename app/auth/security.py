"""JWT verification and role gates.

Deliberately thin: the app trusts any JWT signed with the configured
secret/algorithm and carrying `sub` + `role` claims. Swapping to an external
IdP means changing config (issuer keys) and, at most, this module — no
user-management code exists to migrate.
"""

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.utils import utcnow


class Role(StrEnum):
    CUSTOMER = "customer"
    OPS = "ops"


@dataclass(frozen=True)
class AuthenticatedUser:
    subject: str
    role: Role


_bearer = HTTPBearer(auto_error=False)


def create_token(subject: str, role: Role) -> str:
    settings = get_settings()
    now = utcnow()
    payload = {
        "sub": subject,
        "role": role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return AuthenticatedUser(subject=payload["sub"], role=Role(payload["role"]))
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


def require_ops(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if user.role is not Role.OPS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requires ops role")
    return user
