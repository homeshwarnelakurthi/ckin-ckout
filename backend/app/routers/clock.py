"""Clock in / clock out for the authenticated user."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import TimeEntry, User
from ..payroll_calculator import calculate_shift, is_over_threshold
from ..schemas import ClockResponse, TimeEntryOut

router = APIRouter(prefix="/api", tags=["clock"])
settings = get_settings()


def _open_entry(db: Session, user_id) -> TimeEntry | None:
    return db.scalar(
        select(TimeEntry).where(
            TimeEntry.user_id == user_id, TimeEntry.status == "open"
        )
    )


@router.post("/clock-in", response_model=ClockResponse, status_code=status.HTTP_201_CREATED)
def clock_in(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Application-layer guard (the DB partial unique index is the backstop).
    if _open_entry(db, user.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an open shift. Clock out first.",
        )
    entry = TimeEntry(
        user_id=user.id, clock_in_at=datetime.now(timezone.utc), status="open"
    )
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an open shift. Clock out first.",
        )
    db.refresh(entry)
    return ClockResponse(entry=TimeEntryOut.model_validate(entry), message="Clocked in")


@router.post("/clock-out", response_model=ClockResponse)
def clock_out(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    entry = _open_entry(db, user.id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have no open shift to clock out of.",
        )

    now = datetime.now(timezone.utc)

    # A shift open past the threshold is almost certainly a forgotten clock-out.
    # Flag it for manager review instead of recording a wildly wrong total.
    if is_over_threshold(entry.clock_in_at, now, settings.open_shift_flag_threshold_hours):
        entry.clock_out_at = now
        entry.status = "flagged"
        entry.total_minutes = None
        entry.total_pay = None
        db.commit()
        db.refresh(entry)
        return ClockResponse(
            entry=TimeEntryOut.model_validate(entry),
            message=(
                "This shift ran over "
                f"{settings.open_shift_flag_threshold_hours}h and was flagged "
                "for manager review. It won't be counted toward pay until "
                "resolved."
            ),
        )

    result = calculate_shift(entry.clock_in_at, now, user.hourly_rate)
    entry.clock_out_at = now
    entry.status = "closed"
    entry.total_minutes = result.total_minutes
    entry.total_pay = result.total_pay
    db.commit()
    db.refresh(entry)
    return ClockResponse(entry=TimeEntryOut.model_validate(entry), message="Clocked out")
