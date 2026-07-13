from pydantic import BaseModel

from app.modules.catalog.schemas import LaunchWindowOut


class PriceEstimateOut(BaseModel):
    base_total_cents: int
    multipliers: dict[str, float]
    total_cents: int


class MatchOut(BaseModel):
    launch_window: LaunchWindowOut
    inclination_delta_deg: float
    altitude_delta_km: float
    orbital_score: float
    estimated_price: PriceEstimateOut
