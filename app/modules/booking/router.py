import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import AuthenticatedUser, get_current_user, require_ops
from app.database import get_db
from app.domain.state_machine import InvalidTransitionError
from app.modules.booking.schemas import BookingOut, BookingRequest, QuoteOut, QuoteRequest
from app.modules.booking.service import BookingError, BookingService, QuoteNotFoundError
from app.modules.manifests.schemas import ManifestOut, StateChangeRequest
from app.modules.manifests.service import ManifestNotFoundError

router = APIRouter(prefix="/manifests", tags=["booking"])


def _service(db: Session = Depends(get_db)) -> BookingService:
    return BookingService(db)


@router.post("/{manifest_id}/quotes", response_model=QuoteOut, status_code=status.HTTP_201_CREATED)
def create_quote(
    manifest_id: uuid.UUID,
    body: QuoteRequest,
    svc: BookingService = Depends(_service),
    user: AuthenticatedUser = Depends(get_current_user),
) -> QuoteOut:
    try:
        return svc.create_quote(manifest_id, body.launch_window_id, user)
    except ManifestNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Manifest not found")
    except InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except BookingError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.post("/{manifest_id}/book", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def book(
    manifest_id: uuid.UUID,
    body: BookingRequest,
    svc: BookingService = Depends(_service),
    user: AuthenticatedUser = Depends(get_current_user),
) -> BookingOut:
    try:
        return svc.book(manifest_id, body.quote_id, user)
    except ManifestNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Manifest not found")
    except QuoteNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except BookingError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.post("/{manifest_id}/cancel", response_model=ManifestOut)
def cancel(
    manifest_id: uuid.UUID,
    svc: BookingService = Depends(_service),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ManifestOut:
    try:
        return svc.cancel(manifest_id, user)
    except ManifestNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Manifest not found")
    except InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.post("/{manifest_id}/status", response_model=ManifestOut)
def advance_status(
    manifest_id: uuid.UUID,
    body: StateChangeRequest,
    svc: BookingService = Depends(_service),
    user: AuthenticatedUser = Depends(require_ops),
) -> ManifestOut:
    try:
        return svc.advance(manifest_id, body.to_state, user)
    except ManifestNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Manifest not found")
    except InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except BookingError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
