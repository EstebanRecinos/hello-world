from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.auth.security import Role, create_token
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class DevTokenRequest(BaseModel):
    subject: str
    role: Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/dev-token", response_model=TokenResponse)
def issue_dev_token(body: DevTokenRequest) -> TokenResponse:
    """Development-only token mint. Disabled via ORBITA_ENABLE_DEV_AUTH=false
    once an external IdP issues the JWTs."""
    if not get_settings().enable_dev_auth:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dev auth is disabled")
    return TokenResponse(access_token=create_token(body.subject, body.role))
