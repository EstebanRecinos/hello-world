"""The MVP's only event-bus subscriber: persist every domain event to the
append-only manifest_events table, inside the publisher's transaction."""

from sqlalchemy.orm import Session

from app.domain.events import DomainEvent, event_bus
from app.modules.manifests.models import ManifestEvent


def persist_domain_event(event: DomainEvent, session: Session) -> None:
    session.add(
        ManifestEvent(
            manifest_id=event.manifest_id,
            event_type=event.event_type,
            actor=event.actor,
            from_state=event.from_state,
            to_state=event.to_state,
            data=event.data,
            created_at=event.occurred_at,
        )
    )


def register() -> None:
    event_bus.subscribe(persist_domain_event)
