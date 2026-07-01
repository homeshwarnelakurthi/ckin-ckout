"""Authentication: single-user login."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, TokenResponse, UserOut
from ..security import create_token, rate_limit_ok, reset_rate_limit, verify_secret

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _client_key(request: Request, identifier: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{ip}:{identifier.lower()}"


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    key = _client_key(request, body.username)
    if not rate_limit_ok(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later.",
        )

    user = db.scalar(select(User).where(User.username == body.username.lower()))
    if user is None or not verify_secret(body.password, user.password_hash):
        # Same message either way — don't leak which usernames exist.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    reset_rate_limit(key)
    token = create_token(str(user.id))
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))
