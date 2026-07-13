import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils import utcnow


class User(Base):
    """A customer account. Ops users are not self-registered; they are created
    by seed/command. The JWT `sub` is this row's id (str), which becomes the
    ownership key for manifests."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="customer")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Single-use tokens (hashed) with their expiry.
    verify_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verify_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    reset_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Progressive lockout against brute force.
    failed_logins: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
