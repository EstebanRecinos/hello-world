"""Matching engine: interface + swappable v1 implementation.

v1 orbital compatibility is a simple inclination/altitude comparison within
configured tolerances. The MatchingEngine protocol takes the full manifest
and candidate windows, so a future delta-v transfer engine drops in without
touching callers: it just scores differently.
"""

from dataclasses import dataclass
from typing import Protocol, Sequence

from app.config import Settings, get_settings
from app.modules.catalog.models import LaunchWindow
from app.modules.manifests.models import PayloadManifest


@dataclass(frozen=True)
class MatchCandidate:
    window: LaunchWindow
    inclination_delta_deg: float
    altitude_delta_km: float
    orbital_score: float  # 1.0 = exact orbit; 0.0 = at the tolerance edge


class MatchingEngine(Protocol):
    def match(
        self, manifest: PayloadManifest, candidates: Sequence[LaunchWindow]
    ) -> list[MatchCandidate]: ...


class V1ToleranceMatcher:
    """v1: a window is compatible when it has capacity for the payload's mass
    and volume, and its orbit is within inclination/altitude tolerance."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def match(
        self, manifest: PayloadManifest, candidates: Sequence[LaunchWindow]
    ) -> list[MatchCandidate]:
        inc_tol = self.settings.matching_inclination_tolerance_deg
        alt_tol = self.settings.matching_altitude_tolerance_km
        results: list[MatchCandidate] = []
        for window in candidates:
            if window.remaining_kg < manifest.mass_kg:
                continue
            if window.remaining_m3 < manifest.volume_m3:
                continue
            inc_delta = abs(window.inclination_deg - manifest.target_inclination_deg)
            alt_delta = abs(window.altitude_km - manifest.target_altitude_km)
            if inc_delta > inc_tol or alt_delta > alt_tol:
                continue
            score = 1.0 - (inc_delta / inc_tol + alt_delta / alt_tol) / 2
            results.append(
                MatchCandidate(
                    window=window,
                    inclination_delta_deg=inc_delta,
                    altitude_delta_km=alt_delta,
                    orbital_score=round(score, 4),
                )
            )
        return results


def get_matching_engine() -> MatchingEngine:
    """Composition point: swap the implementation here (or via DI override)."""
    return V1ToleranceMatcher()
