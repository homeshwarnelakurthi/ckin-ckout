"""Password hashing, JWT issue/verify, and a simple login rate limiter."""
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import get_settings

settings = get_settings()


# --- Password hashing (bcrypt, never plaintext) ---
def hash_secret(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_secret(raw: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# --- JWT ---
def create_token(subject: str, expires_minutes: int | None = None) -> str:
    if expires_minutes is None:
        expires_minutes = settings.access_token_expire_minutes
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )


# --- In-memory login rate limiter (per identifier) ---
# Simple sliding window; adequate for a single-instance small deployment. Swap
# for Redis if the app is scaled to multiple instances.
_attempts: dict[str, deque] = defaultdict(deque)


def rate_limit_ok(key: str) -> bool:
    """Record an attempt and return False if the window is exhausted."""
    now = time.monotonic()
    window = settings.login_window_seconds
    bucket = _attempts[key]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= settings.login_max_attempts:
        return False
    bucket.append(now)
    return True


def reset_rate_limit(key: str) -> None:
    _attempts.pop(key, None)
