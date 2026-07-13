"""In-process domain events.

Every relevant action (creation, quoting, booking, state change) publishes a
DomainEvent. In the MVP the only subscriber persists events to the append-only
manifest_events table, inside the caller's transaction. The bus is the seam
for future integrations (notifications, physical-custody systems): subscribe
another handler, publishers don't change.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.utils import utcnow


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    actor: str
    manifest_id: uuid.UUID | None = None
    from_state: str | None = None
    to_state: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=utcnow)


EventHandler = Callable[[DomainEvent, Session], None]


class EventBus:
    """Synchronous bus. Handlers receive the publisher's Session so their
    writes commit or roll back atomically with the action that caused them."""

    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        if handler not in self._handlers:
            self._handlers.append(handler)

    def publish(self, event: DomainEvent, session: Session) -> None:
        for handler in self._handlers:
            handler(event, session)


event_bus = EventBus()
