import uuid
from datetime import datetime

from sqlalchemy import BigInteger, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils import utcnow


class LaunchWindowStatus:
    OPEN = "open"
    CLOSED = "closed"


class LaunchWindow(Base):
    __tablename__ = "launch_windows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(120))
    vehicle: Mapped[str] = mapped_column(String(120))
    launch_date: Mapped[datetime]
    orbit_name: Mapped[str] = mapped_column(String(40))  # e.g. "SSO", "LEO", "GTO"
    inclination_deg: Mapped[float]
    altitude_km: Mapped[float]
    capacity_kg: Mapped[float]
    capacity_m3: Mapped[float]
    remaining_kg: Mapped[float]
    remaining_m3: Mapped[float]
    base_price_cents_per_kg: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default=LaunchWindowStatus.OPEN)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
