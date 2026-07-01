"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import select

from .config import get_settings
from .database import Base, SessionLocal, engine
from .deps import get_current_user
from .models import User
from .routers import auth, clock, timesheet
from .schemas import MetaResponse, UserOut
from .security import hash_secret

settings = get_settings()


def _bootstrap_account() -> None:
    """Create the one real account from env vars if no user exists yet, or —
    if FORCE_PASSWORD_RESET is set — overwrite an existing account's password.
    Safe to run on every startup; a no-op once the account exists and reset
    isn't requested."""
    if not settings.bootstrap_email or not settings.bootstrap_password:
        return
    db = SessionLocal()
    try:
        existing = db.scalar(
            select(User).where(User.email == settings.bootstrap_email.lower())
        )
        if existing is None:
            db.add(
                User(
                    full_name=settings.manager_name,
                    email=settings.bootstrap_email.lower(),
                    password_hash=hash_secret(settings.bootstrap_password),
                    hourly_rate=settings.default_hourly_rate,
                )
            )
            db.commit()
        elif settings.force_password_reset:
            existing.password_hash = hash_secret(settings.bootstrap_password)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create tables if they don't exist. Production should use
    # a migration tool (Alembic) instead — see README.
    Base.metadata.create_all(bind=engine)
    _bootstrap_account()
    yield


app = FastAPI(
    title=f"{settings.business_name} — Time Tracking API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta", response_model=MetaResponse)
def meta():
    """Public branding/config for the frontend."""
    return MetaResponse(
        business_name=settings.business_name,
        manager_name=settings.manager_name,
        display_timezone=settings.display_timezone,
        default_hourly_rate=settings.default_hourly_rate,
    )


@app.get("/api/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return UserOut.model_validate(current)


app.include_router(auth.router)
app.include_router(clock.router)
app.include_router(timesheet.router)
