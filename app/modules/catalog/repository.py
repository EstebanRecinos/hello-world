import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.models import LaunchWindow, LaunchWindowStatus


class LaunchWindowRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, window: LaunchWindow) -> LaunchWindow:
        self.session.add(window)
        return window

    def get(self, window_id: uuid.UUID) -> LaunchWindow | None:
        return self.session.get(LaunchWindow, window_id)

    def list_all(self) -> list[LaunchWindow]:
        return list(
            self.session.scalars(select(LaunchWindow).order_by(LaunchWindow.launch_date))
        )

    def list_open_after(self, moment: datetime) -> list[LaunchWindow]:
        return list(
            self.session.scalars(
                select(LaunchWindow)
                .where(
                    LaunchWindow.status == LaunchWindowStatus.OPEN,
                    LaunchWindow.launch_date > moment,
                )
                .order_by(LaunchWindow.launch_date)
            )
        )

    def delete(self, window: LaunchWindow) -> None:
        self.session.delete(window)
