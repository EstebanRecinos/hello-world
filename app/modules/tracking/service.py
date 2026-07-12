from sqlalchemy.orm import Session

from app.modules.manifests.repository import ManifestRepository
from app.modules.tracking.schemas import TrackingEventOut, TrackingOut


class TrackingTokenNotFoundError(Exception):
    pass


class TrackingService:
    def __init__(self, session: Session) -> None:
        self.repo = ManifestRepository(session)

    def get_by_token(self, token: str) -> TrackingOut:
        manifest = self.repo.get_by_tracking_token(token)
        if manifest is None:
            raise TrackingTokenNotFoundError()
        events = self.repo.list_events(manifest.id)
        return TrackingOut(
            payload_name=manifest.name,
            status=manifest.status,
            target_orbit_name=manifest.target_orbit_name,
            last_updated=manifest.updated_at,
            history=[TrackingEventOut.model_validate(e) for e in events],
        )
