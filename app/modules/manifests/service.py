import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import AuthenticatedUser, Role
from app.domain.events import DomainEvent, event_bus
from app.domain.state_machine import ManifestState, validate_transition
from app.modules.manifests.models import ManifestEvent, PayloadManifest, TriState
from app.modules.manifests.repository import ManifestRepository
from app.modules.manifests.schemas import ManifestCreate, ManifestUpdate, ReviewRequest


class ManifestNotFoundError(Exception):
    pass


class ManifestNotEditableError(Exception):
    pass


class ReviewError(Exception):
    """Invalid review request (wrong state or field not unsure)."""


class IncompleteManifestError(Exception):
    """The manifest is missing fields required for matching/quoting. Carries
    the machine-readable list so the wizard can route the user to the right
    step."""

    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        super().__init__(
            "Manifest is incomplete; fill these fields first: " + ", ".join(missing_fields)
        )


class ManifestService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = ManifestRepository(session)

    def create(self, data: ManifestCreate, customer_id: str) -> PayloadManifest:
        manifest = PayloadManifest(**data.model_dump(), customer_id=customer_id)
        self.repo.add(manifest)
        self.session.flush()
        event_bus.publish(
            DomainEvent(
                event_type="manifest.created",
                actor=customer_id,
                manifest_id=manifest.id,
                to_state=manifest.status,
                data={"name": manifest.name, "mass_kg": manifest.mass_kg},
            ),
            self.session,
        )
        if manifest.needs_review:
            self._emit_review_requested(manifest, actor=customer_id)
        self.session.commit()
        return manifest

    def get_for_user(self, manifest_id: uuid.UUID, user: AuthenticatedUser) -> PayloadManifest:
        """Customers only see their own manifests; ops sees everything."""
        manifest = self.repo.get(manifest_id)
        if manifest is None:
            raise ManifestNotFoundError(str(manifest_id))
        if user.role is not Role.OPS and manifest.customer_id != user.subject:
            # 404, not 403: don't leak existence of other customers' payloads.
            raise ManifestNotFoundError(str(manifest_id))
        return manifest

    def list_for_user(self, user: AuthenticatedUser) -> list[PayloadManifest]:
        if user.role is Role.OPS:
            return self.repo.list_all()
        return self.repo.list_for_customer(user.subject)

    def update(
        self, manifest_id: uuid.UUID, data: ManifestUpdate, user: AuthenticatedUser
    ) -> PayloadManifest:
        manifest = self.get_for_user(manifest_id, user)
        if manifest.state is not ManifestState.DRAFT:
            raise ManifestNotEditableError(
                f"Manifest is {manifest.status!r}; only draft manifests can be edited"
            )
        unsure_before = set(manifest.unsure_fields)
        changes = data.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(manifest, key, value)
        event_bus.publish(
            DomainEvent(
                event_type="manifest.updated",
                actor=user.subject,
                manifest_id=manifest.id,
                data={"changed_fields": sorted(changes)},
            ),
            self.session,
        )
        unsure_after = set(manifest.unsure_fields)
        if unsure_after and unsure_after != unsure_before:
            self._emit_review_requested(manifest, actor=user.subject)
        self.session.commit()
        return manifest

    def review(
        self, manifest_id: uuid.UUID, data: ReviewRequest, user: AuthenticatedUser
    ) -> PayloadManifest:
        """Ops resolves unsure safety answers to definitive yes/no. Allowed in
        draft or quoted; resolving while quoted invalidates active quotes so
        the customer re-quotes at the (possibly lower) correct price — quotes
        themselves are immutable."""
        manifest = self.get_for_user(manifest_id, user)
        if manifest.state not in (ManifestState.DRAFT, ManifestState.QUOTED):
            raise ReviewError(
                f"Manifest is {manifest.status!r}; reviews are only allowed in draft or quoted"
            )
        unsure = set(manifest.unsure_fields)
        not_unsure = sorted(set(data.resolutions) - unsure)
        if not_unsure:
            raise ReviewError(
                f"Fields {not_unsure} are not marked unsure; only unsure answers can be resolved"
            )

        for field, answer in data.resolutions.items():
            setattr(manifest, f"{field}_answer", answer)

        invalidated: list[str] = []
        if manifest.state is ManifestState.QUOTED:
            invalidated = self._invalidate_active_quotes(manifest.id)

        event_bus.publish(
            DomainEvent(
                event_type="manifest.review_resolved",
                actor=user.subject,
                manifest_id=manifest.id,
                data={
                    "resolutions": dict(data.resolutions),
                    "remaining_unsure": manifest.unsure_fields,
                    "invalidated_quotes": invalidated,
                },
            ),
            self.session,
        )
        self.session.commit()
        return manifest

    def _invalidate_active_quotes(self, manifest_id: uuid.UUID) -> list[str]:
        # Local import: booking depends on manifests for transitions; keep the
        # reverse edge model-only to avoid a service-level cycle.
        from app.modules.booking.models import Quote
        from app.utils import utcnow

        quotes = self.session.scalars(
            select(Quote).where(
                Quote.manifest_id == manifest_id, Quote.invalidated_at.is_(None)
            )
        ).all()
        now = utcnow()
        for quote in quotes:
            quote.invalidated_at = now
        return [str(q.id) for q in quotes]

    def _emit_review_requested(self, manifest: PayloadManifest, actor: str) -> None:
        event_bus.publish(
            DomainEvent(
                event_type="manifest.review_requested",
                actor=actor,
                manifest_id=manifest.id,
                data={"unsure_fields": manifest.unsure_fields},
            ),
            self.session,
        )

    def transition(
        self,
        manifest: PayloadManifest,
        to_state: ManifestState,
        actor: str,
        event_type: str = "manifest.state_changed",
        data: dict | None = None,
    ) -> None:
        """Apply a state transition and publish its event. Does NOT commit —
        callers (booking, ops flows) commit once their whole action is done,
        so capacity changes and state changes stay atomic."""
        from_state = manifest.state
        validate_transition(from_state, to_state)
        manifest.status = to_state.value
        event_bus.publish(
            DomainEvent(
                event_type=event_type,
                actor=actor,
                manifest_id=manifest.id,
                from_state=from_state.value,
                to_state=to_state.value,
                data=data or {},
            ),
            self.session,
        )

    def list_events(self, manifest_id: uuid.UUID) -> list[ManifestEvent]:
        return self.repo.list_events(manifest_id)


# Re-exported for callers that need to validate answers.
__all__ = [
    "ManifestService",
    "ManifestNotFoundError",
    "ManifestNotEditableError",
    "ReviewError",
    "TriState",
]
