import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils import as_utc


def _require_timezone(v: datetime | None) -> datetime | None:
    if v is not None and v.tzinfo is None:
        raise ValueError("launch_date must be timezone-aware (UTC)")
    return v


class LaunchWindowBase(BaseModel):
    provider: str = Field(min_length=1, max_length=120)
    vehicle: str = Field(min_length=1, max_length=120)
    launch_date: datetime
    orbit_name: str = Field(min_length=1, max_length=40)
    inclination_deg: float = Field(ge=0, le=180)
    altitude_km: float = Field(gt=0)
    capacity_kg: float = Field(gt=0)
    capacity_m3: float = Field(gt=0)
    base_price_cents_per_kg: int = Field(gt=0, description="USD cents per kg; money is always integer cents")


class LaunchWindowCreate(LaunchWindowBase):
    require_tz = field_validator("launch_date")(_require_timezone)


class LaunchWindowUpdate(BaseModel):
    launch_date: datetime | None = None
    base_price_cents_per_kg: int | None = Field(default=None, gt=0)
    status: str | None = Field(default=None, pattern="^(open|closed)$")

    require_tz = field_validator("launch_date")(_require_timezone)


class LaunchWindowOut(LaunchWindowBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    remaining_kg: float
    remaining_m3: float
    status: str
    created_at: datetime

    # SQLite round-trips datetimes without tzinfo; everything stored is UTC.
    normalize_tz = field_validator("launch_date", "created_at")(
        lambda v: as_utc(v) if isinstance(v, datetime) else v
    )
