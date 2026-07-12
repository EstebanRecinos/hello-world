import uuid

from sqlalchemy.orm import Session

from app.auth.security import AuthenticatedUser
from app.modules.catalog.repository import LaunchWindowRepository
from app.modules.manifests.service import ManifestService
from app.modules.matching.engine import MatchingEngine, get_matching_engine
from app.modules.matching.schemas import MatchOut, PriceEstimateOut
from app.modules.pricing.engine import PricingEngine, get_pricing_engine
from app.utils import as_utc, utcnow


class MatchingService:
    def __init__(
        self,
        session: Session,
        matcher: MatchingEngine | None = None,
        pricer: PricingEngine | None = None,
    ) -> None:
        self.session = session
        self.matcher = matcher or get_matching_engine()
        self.pricer = pricer or get_pricing_engine()
        self.windows = LaunchWindowRepository(session)
        self.manifests = ManifestService(session)

    def find_matches(self, manifest_id: uuid.UUID, user: AuthenticatedUser) -> list[MatchOut]:
        """Compatible windows ranked by (a) orbital score desc, (b) launch
        date asc, (c) price asc — deterministic lexicographic ranking."""
        manifest = self.manifests.get_for_user(manifest_id, user)
        candidates = self.windows.list_open_after(utcnow())
        matches = self.matcher.match(manifest, candidates)

        priced = []
        for m in matches:
            breakdown = self.pricer.quote(manifest, m.window)
            priced.append((m, breakdown))

        priced.sort(
            key=lambda pair: (
                -pair[0].orbital_score,
                as_utc(pair[0].window.launch_date),
                pair[1].total_cents,
            )
        )
        return [
            MatchOut(
                launch_window=pair[0].window,
                inclination_delta_deg=pair[0].inclination_delta_deg,
                altitude_delta_km=pair[0].altitude_delta_km,
                orbital_score=pair[0].orbital_score,
                estimated_price=PriceEstimateOut(
                    base_total_cents=pair[1].base_total_cents,
                    multipliers=pair[1].multipliers,
                    total_cents=pair[1].total_cents,
                ),
            )
            for pair in priced
        ]
