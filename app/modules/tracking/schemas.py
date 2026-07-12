from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.utils import as_utc


class TrackingEventOut(BaseModel):
    """Public history entry: event type and state change only. Actor and raw
    event data stay internal."""

    model_config = ConfigDict(from_attributes=True)

    event_type: str
    from_state: str | None
    to_state: str | None
    created_at: datetime

    normalize_tz = field_validator("created_at")(as_utc)


class TrackingOut(BaseModel):
    payload_name: str
    status: str
    target_orbit_name: str
    last_updated: datetime
    history: list[TrackingEventOut]

    normalize_tz = field_validator("last_updated")(as_utc)
