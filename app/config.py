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
    # Dev token issuer. Leave true for local/tests; production sets it false
    # once real accounts (or an external IdP) issue the JWTs.
    enable_dev_auth: bool = True

    # Accounts: password hashing and single-use token lifetimes.
    account_pbkdf2_iterations: int = 240_000
    account_verify_ttl_hours: int = 24
    account_reset_ttl_hours: int = 1
    account_max_failed_logins: int = 5
    account_lockout_minutes: int = 15
    # Base URL the app builds verification / reset links against.
    public_base_url: str = "http://localhost:8000"

    # Email delivery. backend="console" logs the message (dev); "smtp" sends it.
    email_backend: str = "console"
    email_from: str = "ORBITA-LINK <no-reply@orbita.link>"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True

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
