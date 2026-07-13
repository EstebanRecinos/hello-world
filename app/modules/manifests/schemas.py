import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.domain.state_machine import ManifestState


def _coerce_tristate(v: Any) -> Any:
    """Backward compatibility: booleans are still accepted (true→yes, false→no)."""
    if isinstance(v, bool):
        return "yes" if v else "no"
    return v


TriStateAnswer = Annotated[Literal["yes", "no", "unsure"], BeforeValidator(_coerce_tristate)]


class ManifestCreate(BaseModel):
    """Only name is required: draft manifests may be partial so the wizard can
    save progress server-side. Completeness is enforced when matching/quoting."""

    name: str = Field(min_length=1, max_length=200)
    mass_kg: float | None = Field(default=None, gt=0, le=500, description="MVP serves smallsats of 1-500 kg")
    length_m: float | None = Field(default=None, gt=0)
    width_m: float | None = Field(default=None, gt=0)
    height_m: float | None = Field(default=None, gt=0)
    target_orbit_name: str | None = Field(default=None, min_length=1, max_length=40)
    target_inclination_deg: float | None = Field(default=None, ge=0, le=180)
    target_altitude_km: float | None = Field(default=None, gt=0)
    has_propulsion: TriStateAnswer = "no"
    hazardous_materials: TriStateAnswer = "no"
    needs_early_deploy: TriStateAnswer = "no"
    itar_controlled: TriStateAnswer = "no"
    licensing_status: Literal["not_required", "pending", "approved"] = "pending"


class ManifestUpdate(BaseModel):
    """Only draft manifests are editable; enforced by the service."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    mass_kg: float | None = Field(default=None, gt=0, le=500)
    length_m: float | None = Field(default=None, gt=0)
    width_m: float | None = Field(default=None, gt=0)
    height_m: float | None = Field(default=None, gt=0)
    target_orbit_name: str | None = Field(default=None, min_length=1, max_length=40)
    target_inclination_deg: float | None = Field(default=None, ge=0, le=180)
    target_altitude_km: float | None = Field(default=None, gt=0)
    has_propulsion: TriStateAnswer | None = None
    hazardous_materials: TriStateAnswer | None = None
    needs_early_deploy: TriStateAnswer | None = None
    itar_controlled: TriStateAnswer | None = None
    licensing_status: Literal["not_required", "pending", "approved"] | None = None


class ManifestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: str
    name: str

    mass_kg: float | None
    length_m: float | None
    width_m: float | None
    height_m: float | None
    volume_m3: float | None
    target_orbit_name: str | None
    target_inclination_deg: float | None
    target_altitude_km: float | None

    # Derived conservative booleans (unsure counts as true) — the original
    # contract — plus the underlying tri-state answers.
    has_propulsion: bool
    hazardous_materials: bool
    needs_early_deploy: bool
    itar_controlled: bool
    has_propulsion_answer: Literal["yes", "no", "unsure"]
    hazardous_materials_answer: Literal["yes", "no", "unsure"]
    needs_early_deploy_answer: Literal["yes", "no", "unsure"]
    itar_controlled_answer: Literal["yes", "no", "unsure"]
    licensing_status: Literal["not_required", "pending", "approved"]

    needs_review: bool
    unsure_fields: list[str]
    is_complete: bool
    missing_fields: list[str]

    status: ManifestState
    tracking_token: str
    created_at: datetime
    updated_at: datetime


class StateChangeRequest(BaseModel):
    to_state: ManifestState


class ReviewRequest(BaseModel):
    """Ops resolves each unsure safety answer to a definitive yes/no."""

    resolutions: dict[
        Literal["has_propulsion", "hazardous_materials", "needs_early_deploy", "itar_controlled"],
        Literal["yes", "no"],
    ] = Field(min_length=1)


class ManifestEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type: str
    actor: str
    from_state: str | None
    to_state: str | None
    data: dict[str, Any]
    created_at: datetime
