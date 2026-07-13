import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.manifests.models import ManifestEvent, PayloadManifest


class ManifestRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, manifest: PayloadManifest) -> PayloadManifest:
        self.session.add(manifest)
        return manifest

    def get(self, manifest_id: uuid.UUID) -> PayloadManifest | None:
        return self.session.get(PayloadManifest, manifest_id)

    def get_by_tracking_token(self, token: str) -> PayloadManifest | None:
        return self.session.scalar(
            select(PayloadManifest).where(PayloadManifest.tracking_token == token)
        )

    def list_for_customer(self, customer_id: str) -> list[PayloadManifest]:
        return list(
            self.session.scalars(
                select(PayloadManifest)
                .where(PayloadManifest.customer_id == customer_id)
                .order_by(PayloadManifest.created_at.desc())
            )
        )

    def list_all(self) -> list[PayloadManifest]:
        return list(
            self.session.scalars(
                select(PayloadManifest).order_by(PayloadManifest.created_at.desc())
            )
        )

    def list_events(self, manifest_id: uuid.UUID) -> list[ManifestEvent]:
        return list(
            self.session.scalars(
                select(ManifestEvent)
                .where(ManifestEvent.manifest_id == manifest_id)
                .order_by(ManifestEvent.id)
            )
        )
