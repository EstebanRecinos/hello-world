import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import AuthenticatedUser, get_current_user, require_ops
from app.database import get_db
from app.modules.manifests.schemas import (
    ManifestCreate,
    ManifestEventOut,
    ManifestOut,
    ManifestUpdate,
    ReviewRequest,
)
from app.modules.manifests.service import (
    ManifestNotEditableError,
    ManifestNotFoundError,
    ManifestService,
    ReviewError,
)

router = APIRouter(prefix="/manifests", tags=["manifests"])


def _service(db: Session = Depends(get_db)) -> ManifestService:
    return ManifestService(db)


@router.post("", response_model=ManifestOut, status_code=status.HTTP_201_CREATED)
def create_manifest(
    body: ManifestCreate,
    svc: ManifestService = Depends(_service),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ManifestOut:
    return svc.create(body, customer_id=user.subject)


@router.get("", response_model=list[ManifestOut])
def list_manifests(
    svc: ManifestService = Depends(_service),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[ManifestOut]:
    return svc.list_for_user(user)


@router.get("/{manifest_id}", response_model=ManifestOut)
def get_manifest(
    manifest_id: uuid.UUID,
    svc: ManifestService = Depends(_service),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ManifestOut:
    try:
        return svc.get_for_user(manifest_id, user)
    except ManifestNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Manifest not found")


@router.patch("/{manifest_id}", response_model=ManifestOut)
def update_manifest(
    manifest_id: uuid.UUID,
    body: ManifestUpdate,
    svc: ManifestService = Depends(_service),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ManifestOut:
    try:
        return svc.update(manifest_id, body, user)
    except ManifestNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Manifest not found")
    except ManifestNotEditableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.post("/{manifest_id}/review", response_model=ManifestOut)
def review_manifest(
    manifest_id: uuid.UUID,
    body: ReviewRequest,
    svc: ManifestService = Depends(_service),
    user: AuthenticatedUser = Depends(require_ops),
) -> ManifestOut:
    """Ops resolves 'unsure' safety answers to definitive yes/no."""
    try:
        return svc.review(manifest_id, body, user)
    except ManifestNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Manifest not found")
    except ReviewError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("/{manifest_id}/events", response_model=list[ManifestEventOut])
def list_manifest_events(
    manifest_id: uuid.UUID,
    svc: ManifestService = Depends(_service),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[ManifestEventOut]:
    try:
        svc.get_for_user(manifest_id, user)
    except ManifestNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Manifest not found")
    return svc.list_events(manifest_id)
