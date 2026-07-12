import secrets
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.domain.state_machine import ManifestState
from app.utils import utcnow


def _new_tracking_token() -> str:
    return secrets.token_urlsafe(24)


class LicensingStatus:
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"

    ALL = (NOT_REQUIRED, PENDING, APPROVED)


class PayloadManifest(Base):
    """The digital payload manifest — the central domain object. It travels
    intact through the whole lifecycle; future phases extend it to physical
    custody and orbital transfer, which is why identity (id, tracking_token)
    and history (manifest_events) are decoupled from any single booking."""

    __tablename__ = "payload_manifests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(200))

    mass_kg: Mapped[float]
    length_m: Mapped[float]
    width_m: Mapped[float]
    height_m: Mapped[float]

    target_orbit_name: Mapped[str] = mapped_column(String(40))
    target_inclination_deg: Mapped[float]
    target_altitude_km: Mapped[float]

    has_propulsion: Mapped[bool] = mapped_column(default=False)
    hazardous_materials: Mapped[bool] = mapped_column(default=False)
    needs_early_deploy: Mapped[bool] = mapped_column(default=False)
    itar_controlled: Mapped[bool] = mapped_column(default=False)
    licensing_status: Mapped[str] = mapped_column(String(20), default=LicensingStatus.PENDING)

    status: Mapped[str] = mapped_column(String(20), default=ManifestState.DRAFT.value, index=True)
    tracking_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=_new_tracking_token
    )

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    @property
    def volume_m3(self) -> float:
        return self.length_m * self.width_m * self.height_m

    @property
    def state(self) -> ManifestState:
        return ManifestState(self.status)


class ManifestEvent(Base):
    """Append-only event log. Rows are only ever INSERTed — no update or
    delete path exists in the application, and none should be added."""

    __tablename__ = "manifest_events"

    # BigInteger in Postgres; SQLite (tests) needs plain INTEGER for autoincrement.
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("payload_manifests.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(80))
    actor: Mapped[str] = mapped_column(String(120))
    from_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
