import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class QuoteRequest(BaseModel):
    launch_window_id: uuid.UUID


class QuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    manifest_id: uuid.UUID
    launch_window_id: uuid.UUID
    base_total_cents: int
    multipliers: dict[str, Any]
    total_cents: int
    expires_at: datetime | None
    invalidated_at: datetime | None
    created_at: datetime


class BookingRequest(BaseModel):
    quote_id: uuid.UUID


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    manifest_id: uuid.UUID
    launch_window_id: uuid.UUID
    quote_id: uuid.UUID
    total_cents: int
    status: str
    created_at: datetime
