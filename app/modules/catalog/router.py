import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import AuthenticatedUser, get_current_user, require_ops
from app.database import get_db
from app.modules.catalog.schemas import LaunchWindowCreate, LaunchWindowOut, LaunchWindowUpdate
from app.modules.catalog.service import CatalogService, LaunchWindowNotFoundError

router = APIRouter(prefix="/launches", tags=["catalog"])


def _service(db: Session = Depends(get_db)) -> CatalogService:
    return CatalogService(db)


@router.post("", response_model=LaunchWindowOut, status_code=status.HTTP_201_CREATED)
def create_launch_window(
    body: LaunchWindowCreate,
    svc: CatalogService = Depends(_service),
    user: AuthenticatedUser = Depends(require_ops),
) -> LaunchWindowOut:
    return svc.create(body, actor=user.subject)


@router.get("", response_model=list[LaunchWindowOut])
def list_launch_windows(
    svc: CatalogService = Depends(_service),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[LaunchWindowOut]:
    return svc.list_all()


@router.get("/{window_id}", response_model=LaunchWindowOut)
def get_launch_window(
    window_id: uuid.UUID,
    svc: CatalogService = Depends(_service),
    _: AuthenticatedUser = Depends(get_current_user),
) -> LaunchWindowOut:
    try:
        return svc.get(window_id)
    except LaunchWindowNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Launch window not found")


@router.patch("/{window_id}", response_model=LaunchWindowOut)
def update_launch_window(
    window_id: uuid.UUID,
    body: LaunchWindowUpdate,
    svc: CatalogService = Depends(_service),
    user: AuthenticatedUser = Depends(require_ops),
) -> LaunchWindowOut:
    try:
        return svc.update(window_id, body, actor=user.subject)
    except LaunchWindowNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Launch window not found")


@router.delete("/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_launch_window(
    window_id: uuid.UUID,
    svc: CatalogService = Depends(_service),
    user: AuthenticatedUser = Depends(require_ops),
) -> None:
    try:
        svc.delete(window_id, actor=user.subject)
    except LaunchWindowNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Launch window not found")
