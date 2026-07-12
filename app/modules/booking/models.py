import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils import utcnow


class Quote(Base):
    """A priced offer of a specific launch window for a specific manifest.
    Booking always references a quote, so the price the customer accepted is
    immutable and auditable."""

    __tablename__ = "quotes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    manifest_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("payload_manifests.id"), index=True
    )
    launch_window_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("launch_windows.id"))
    base_total_cents: Mapped[int] = mapped_column(BigInteger)
    multipliers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    total_cents: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class BookingStatus:
    ACTIVE = "active"
    CANCELLED = "cancelled"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    manifest_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("payload_manifests.id"), unique=True, index=True
    )
    launch_window_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("launch_windows.id"))
    quote_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("quotes.id"))
    total_cents: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default=BookingStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
