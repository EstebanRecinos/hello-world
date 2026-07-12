from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.tracking.schemas import TrackingOut
from app.modules.tracking.service import TrackingService, TrackingTokenNotFoundError

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/{tracking_token}", response_model=TrackingOut)
def track_payload(tracking_token: str, db: Session = Depends(get_db)) -> TrackingOut:
    """Public endpoint: the unguessable tracking token is the credential."""
    try:
        return TrackingService(db).get_by_token(tracking_token)
    except TrackingTokenNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown tracking token")
