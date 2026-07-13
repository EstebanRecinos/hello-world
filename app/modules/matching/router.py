import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import AuthenticatedUser, get_current_user
from app.database import get_db
from app.modules.manifests.service import IncompleteManifestError, ManifestNotFoundError
from app.modules.matching.schemas import MatchOut
from app.modules.matching.service import MatchingService

router = APIRouter(prefix="/manifests", tags=["matching"])


def _service(db: Session = Depends(get_db)) -> MatchingService:
    return MatchingService(db)


@router.get("/{manifest_id}/matches", response_model=list[MatchOut])
def find_matches(
    manifest_id: uuid.UUID,
    svc: MatchingService = Depends(_service),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[MatchOut]:
    try:
        return svc.find_matches(manifest_id, user)
    except ManifestNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Manifest not found")
    except IncompleteManifestError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"message": str(exc), "missing_fields": exc.missing_fields},
        )
