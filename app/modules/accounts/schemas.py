import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

# Deliberately permissive: reject the obviously-malformed, let real delivery
# (the verification email) prove the address. Avoids an email-validator dep.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _valid_email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL_RE.match(v) or len(v) > 254:
        raise ValueError("Invalid email address")
    return v


Email = Annotated[str, AfterValidator(_valid_email)]


class RegisterRequest(BaseModel):
    email: Email
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: Email
    password: str = Field(min_length=1, max_length=200)


class VerifyRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class RequestResetRequest(BaseModel):
    email: Email


class ResetRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    role: str
    email_verified: bool
    created_at: datetime


class MessageResponse(BaseModel):
    message: str
