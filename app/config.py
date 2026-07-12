from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ORBITA_", extra="ignore")

    database_url: str = "postgresql+psycopg://orbita:orbita@localhost:5432/orbita"

    # Auth. Dev-token issuance is a stand-in for an external IdP: the app only
    # *verifies* JWTs, so pointing jwt_secret/algorithm at the IdP's config is
    # the whole migration.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60
    enable_dev_auth: bool = True

    # Matching v1 tolerances
    matching_inclination_tolerance_deg: float = 1.5
    matching_altitude_tolerance_km: float = 50.0

    # Quotes: hours until a quote expires; 0 or negative = never expires
    quote_ttl_hours: int = 72

    # Pricing v1 multipliers — configuration, not code
    pricing_urgency_days_threshold: int = 90
    pricing_urgency_multiplier: float = 1.25
    pricing_atypical_volume_density_kg_m3: float = 250.0
    pricing_atypical_volume_multiplier: float = 1.15
    pricing_regulatory_risk_multiplier: float = 1.20


@lru_cache
def get_settings() -> Settings:
    return Settings()
