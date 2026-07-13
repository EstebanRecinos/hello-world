import uuid

from sqlalchemy.orm import Session

from app.domain.events import DomainEvent, event_bus
from app.modules.catalog.models import LaunchWindow
from app.modules.catalog.repository import LaunchWindowRepository
from app.modules.catalog.schemas import LaunchWindowCreate, LaunchWindowUpdate


class LaunchWindowNotFoundError(Exception):
    pass


class CatalogService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = LaunchWindowRepository(session)

    def create(self, data: LaunchWindowCreate, actor: str) -> LaunchWindow:
        window = LaunchWindow(
            **data.model_dump(),
            remaining_kg=data.capacity_kg,
            remaining_m3=data.capacity_m3,
        )
        self.repo.add(window)
        self.session.flush()
        event_bus.publish(
            DomainEvent(
                event_type="launch_window.created",
                actor=actor,
                data={"launch_window_id": str(window.id), "provider": window.provider},
            ),
            self.session,
        )
        self.session.commit()
        return window

    def get(self, window_id: uuid.UUID) -> LaunchWindow:
        window = self.repo.get(window_id)
        if window is None:
            raise LaunchWindowNotFoundError(str(window_id))
        return window

    def list_all(self) -> list[LaunchWindow]:
        return self.repo.list_all()

    def update(self, window_id: uuid.UUID, data: LaunchWindowUpdate, actor: str) -> LaunchWindow:
        window = self.get(window_id)
        changes = data.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(window, key, value)
        event_bus.publish(
            DomainEvent(
                event_type="launch_window.updated",
                actor=actor,
                data={"launch_window_id": str(window.id), "changes": {k: str(v) for k, v in changes.items()}},
            ),
            self.session,
        )
        self.session.commit()
        return window

    def delete(self, window_id: uuid.UUID, actor: str) -> None:
        window = self.get(window_id)
        self.repo.delete(window)
        event_bus.publish(
            DomainEvent(
                event_type="launch_window.deleted",
                actor=actor,
                data={"launch_window_id": str(window_id)},
            ),
            self.session,
        )
        self.session.commit()
