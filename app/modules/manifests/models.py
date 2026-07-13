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


class TriState:
    """Answer to a safety question. UNSURE is a valid customer answer: it is
    priced conservatively (like YES) and flags the manifest for human review."""

    YES = "yes"
    NO = "no"
    UNSURE = "unsure"

    ALL = (YES, NO, UNSURE)


# The four safety questions, in the order they are asked.
SAFETY_FIELDS = (
    "has_propulsion",
    "hazardous_materials",
    "needs_early_deploy",
    "itar_controlled",
)

# Fields that must be filled before the manifest can be matched or quoted.
# Draft manifests may leave them empty (partial drafts for the wizard).
REQUIRED_FOR_QUOTE = (
    "mass_kg",
    "length_m",
    "width_m",
    "height_m",
    "target_orbit_name",
    "target_inclination_deg",
    "target_altitude_km",
)


def _tristate_bool_property(field: str):
    """Derived boolean view of a tri-state answer column. Reading is
    conservative (unsure counts as True); writing accepts both booleans
    (backward compatibility) and tri-state strings."""

    column = f"{field}_answer"

    def getter(self) -> bool:
        answer = getattr(self, column)
        # None = column default not yet applied (instance not flushed) = "no".
        return answer is not None and answer != TriState.NO

    def setter(self, value) -> None:
        if isinstance(value, bool):
            value = TriState.YES if value else TriState.NO
        if value not in TriState.ALL:
            raise ValueError(f"{field} must be a bool or one of {TriState.ALL}")
        setattr(self, column, value)

    return property(getter, setter)


class PayloadManifest(Base):
    """The digital payload manifest — the central domain object. It travels
    intact through the whole lifecycle; future phases extend it to physical
    custody and orbital transfer, which is why identity (id, tracking_token)
    and history (manifest_events) are decoupled from any single booking."""

    __tablename__ = "payload_manifests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(200))

    # Nullable while in draft: the wizard saves partial progress server-side.
    mass_kg: Mapped[float | None]
    length_m: Mapped[float | None]
    width_m: Mapped[float | None]
    height_m: Mapped[float | None]

    target_orbit_name: Mapped[str | None] = mapped_column(String(40))
    target_inclination_deg: Mapped[float | None]
    target_altitude_km: Mapped[float | None]

    # Tri-state safety answers (yes / no / unsure).
    has_propulsion_answer: Mapped[str] = mapped_column(String(10), default=TriState.NO)
    hazardous_materials_answer: Mapped[str] = mapped_column(String(10), default=TriState.NO)
    needs_early_deploy_answer: Mapped[str] = mapped_column(String(10), default=TriState.NO)
    itar_controlled_answer: Mapped[str] = mapped_column(String(10), default=TriState.NO)
    licensing_status: Mapped[str] = mapped_column(String(20), default=LicensingStatus.PENDING)

    status: Mapped[str] = mapped_column(String(20), default=ManifestState.DRAFT.value, index=True)
    tracking_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=_new_tracking_token
    )

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    # Derived boolean views: unsure prices and gates conservatively as True.
    has_propulsion = _tristate_bool_property("has_propulsion")
    hazardous_materials = _tristate_bool_property("hazardous_materials")
    needs_early_deploy = _tristate_bool_property("needs_early_deploy")
    itar_controlled = _tristate_bool_property("itar_controlled")

    @property
    def volume_m3(self) -> float | None:
        if self.length_m is None or self.width_m is None or self.height_m is None:
            return None
        return self.length_m * self.width_m * self.height_m

    @property
    def missing_fields(self) -> list[str]:
        return [f for f in REQUIRED_FOR_QUOTE if getattr(self, f) is None]

    @property
    def is_complete(self) -> bool:
        return not self.missing_fields

    @property
    def unsure_fields(self) -> list[str]:
        return [f for f in SAFETY_FIELDS if getattr(self, f + "_answer") == TriState.UNSURE]

    @property
    def needs_review(self) -> bool:
        return bool(self.unsure_fields)

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
