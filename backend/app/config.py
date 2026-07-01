"""Application configuration.

All tunable values live here so nothing important is hardcoded in the code
paths. Values are read from the environment (see `.env.example`) and can be
overridden per-deployment via the cloud provider's secret manager.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Branding (surfaced to the frontend via /api/meta) ---
    business_name: str = "CK_IN&CK_OUT"
    manager_name: str = "Hpatel"

    # --- Database ---
    # Single-user app: a local SQLite file is simplest and needs no separate
    # DB server. Swap for a Postgres URL if this ever needs to scale up.
    database_url: str = "sqlite+pysqlite:///./dev.db"

    # --- Auth / JWT ---
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 12 * 60  # normal web session

    # --- Login rate limiting ---
    login_max_attempts: int = 5
    login_window_seconds: int = 300  # 5 minutes

    # --- Payroll ---
    # Default rate. Per-user overrides live in users.hourly_rate.
    default_hourly_rate: float = 10.00

    # --- Shift rules ---
    # A shift left open longer than this is auto-flagged for manager review
    # instead of being counted toward pay.
    open_shift_flag_threshold_hours: int = 14

    # --- Display ---
    # Timestamps are stored in UTC; the frontend renders them in this zone.
    display_timezone: str = "America/New_York"

    # --- CORS (frontend origin) ---
    frontend_origin: str = "http://localhost:5173"

    # --- First-boot account bootstrap ---
    # If set and no user exists yet, the app creates exactly one real account
    # from these on startup — no fake seed data. Set these as secrets on the
    # host (e.g. Render env vars), then unset/rotate the password afterward.
    # Plain numbers are fine, e.g. username "123", password "1234".
    bootstrap_username: str | None = None
    bootstrap_password: str | None = None

    # Forgot your password and have no DB shell access? Set BOOTSTRAP_PASSWORD
    # to a new value and this to true, then restart — the existing account's
    # password is overwritten on next boot. Turn it back off afterward so a
    # future restart can't silently reset it again.
    force_password_reset: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
