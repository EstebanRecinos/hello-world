import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.state_machine import ManifestState


class ManifestBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mass_kg: float = Field(gt=0, le=500, description="MVP serves smallsats of 1-500 kg")
    length_m: float = Field(gt=0)
    width_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    target_orbit_name: str = Field(min_length=1, max_length=40)
    target_inclination_deg: float = Field(ge=0, le=180)
    target_altitude_km: float = Field(gt=0)
    has_propulsion: bool = False
    hazardous_materials: bool = False
    needs_early_deploy: bool = False
    itar_controlled: bool = False
    licensing_status: Literal["not_required", "pending", "approved"] = "pending"


class ManifestCreate(ManifestBase):
    pass


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
    has_propulsion: bool | None = None
    hazardous_materials: bool | None = None
    needs_early_deploy: bool | None = None
    itar_controlled: bool | None = None
    licensing_status: Literal["not_required", "pending", "approved"] | None = None


class ManifestOut(ManifestBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: str
    volume_m3: float
    status: ManifestState
    tracking_token: str
    created_at: datetime
    updated_at: datetime


class StateChangeRequest(BaseModel):
    to_state: ManifestState


class ManifestEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type: str
    actor: str
    from_state: str | None
    to_state: str | None
    data: dict[str, Any]
    created_at: datetime
