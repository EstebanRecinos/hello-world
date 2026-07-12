import uuid

from sqlalchemy.orm import Session

from app.auth.security import AuthenticatedUser, Role
from app.domain.events import DomainEvent, event_bus
from app.domain.state_machine import ManifestState, validate_transition
from app.modules.manifests.models import ManifestEvent, PayloadManifest
from app.modules.manifests.repository import ManifestRepository
from app.modules.manifests.schemas import ManifestCreate, ManifestUpdate


class ManifestNotFoundError(Exception):
    pass


class ManifestNotEditableError(Exception):
    pass


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
        self.session.commit()
        return manifest

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
