"""Pricing engine: interface + swappable v1 implementation.

price = launch base rate x kg x multipliers. Multipliers live in Settings
(environment), never in code. Money is always integer USD cents.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from app.config import Settings, get_settings
from app.modules.catalog.models import LaunchWindow
from app.modules.manifests.models import LicensingStatus, PayloadManifest
from app.utils import as_utc, utcnow


@dataclass(frozen=True)
class PriceBreakdown:
    base_price_cents_per_kg: int
    mass_kg: float
    base_total_cents: int
    multipliers: dict[str, float]  # name -> factor, only the ones that applied
    total_cents: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_price_cents_per_kg": self.base_price_cents_per_kg,
            "mass_kg": self.mass_kg,
            "base_total_cents": self.base_total_cents,
            "multipliers": self.multipliers,
            "total_cents": self.total_cents,
        }


class PricingEngine(Protocol):
    def quote(
        self, manifest: PayloadManifest, window: LaunchWindow, *, now: datetime | None = None
    ) -> PriceBreakdown: ...


class V1MultiplierPricing:
    """v1: base rate x kg, then urgency / atypical-volume / regulatory-risk
    multipliers from configuration."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def quote(
        self, manifest: PayloadManifest, window: LaunchWindow, *, now: datetime | None = None
    ) -> PriceBreakdown:
        s = self.settings
        now = now or utcnow()
        base_total = round(window.base_price_cents_per_kg * manifest.mass_kg)

        multipliers: dict[str, float] = {}

        days_to_launch = (as_utc(window.launch_date) - now).total_seconds() / 86_400
        if days_to_launch < s.pricing_urgency_days_threshold:
            multipliers["urgency"] = s.pricing_urgency_multiplier

        # Low density = bulky payload: it consumes volume faster than mass.
        density = manifest.mass_kg / manifest.volume_m3
        if density < s.pricing_atypical_volume_density_kg_m3:
            multipliers["atypical_volume"] = s.pricing_atypical_volume_multiplier

        licensing_incomplete = manifest.licensing_status == LicensingStatus.PENDING
        itar_unresolved = (
            manifest.itar_controlled
            and manifest.licensing_status != LicensingStatus.APPROVED
        )
        if manifest.hazardous_materials or licensing_incomplete or itar_unresolved:
            multipliers["regulatory_risk"] = s.pricing_regulatory_risk_multiplier

        total = base_total
        for factor in multipliers.values():
            total = round(total * factor)

        return PriceBreakdown(
            base_price_cents_per_kg=window.base_price_cents_per_kg,
            mass_kg=manifest.mass_kg,
            base_total_cents=base_total,
            multipliers=multipliers,
            total_cents=total,
        )


def get_pricing_engine() -> PricingEngine:
    """Composition point: swap the implementation here (or via DI override)."""
    return V1MultiplierPricing()
