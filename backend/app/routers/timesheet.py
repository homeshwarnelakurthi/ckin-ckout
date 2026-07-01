"""Self-service timesheet: history, summary, corrections, and CSV export."""
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import EntryAuditLog, TimeEntry, User
from ..payroll_calculator import aggregate, calculate_shift
from ..schemas import EntryPatchRequest, SummaryPeriod, SummaryResponse, TimeEntryOut
from ..timeutils import day_bounds_utc, month_bounds_utc, week_bounds_utc

router = APIRouter(prefix="/api/timesheet", tags=["timesheet"])
settings = get_settings()


def _entries_between(db: Session, user_id, start, end) -> list[TimeEntry]:
    return list(
        db.scalars(
            select(TimeEntry)
            .where(
                TimeEntry.user_id == user_id,
                TimeEntry.clock_in_at >= start,
                TimeEntry.clock_in_at < end,
            )
            .order_by(TimeEntry.clock_in_at.desc())
        )
    )


def _period(entries: list[TimeEntry]) -> SummaryPeriod:
    totals = aggregate(
        [
            {"status": e.status, "total_minutes": e.total_minutes, "total_pay": e.total_pay}
            for e in entries
        ]
    )
    return SummaryPeriod(
        total_minutes=totals.total_minutes,
        total_hours=totals.total_hours,
        total_pay=totals.total_pay,
    )


@router.get("/me", response_model=list[TimeEntryOut])
def my_entries(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(TimeEntry).where(TimeEntry.user_id == user.id)
    if from_:
        stmt = stmt.where(TimeEntry.clock_in_at >= from_)
    if to:
        stmt = stmt.where(TimeEntry.clock_in_at < to)
    stmt = stmt.order_by(TimeEntry.clock_in_at.desc())
    return [TimeEntryOut.model_validate(e) for e in db.scalars(stmt)]


@router.get("/me/summary", response_model=SummaryResponse)
def my_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tz = settings.display_timezone
    now = datetime.now(timezone.utc)

    d_start, d_end = day_bounds_utc(tz, now)
    w_start, w_end = week_bounds_utc(tz, now)
    m_start, m_end = month_bounds_utc(tz, now)

    open_entry = db.scalar(
        select(TimeEntry).where(
            TimeEntry.user_id == user.id, TimeEntry.status == "open"
        )
    )

    return SummaryResponse(
        today=_period(_entries_between(db, user.id, d_start, d_end)),
        week=_period(_entries_between(db, user.id, w_start, w_end)),
        month=_period(_entries_between(db, user.id, m_start, m_end)),
        open_entry=TimeEntryOut.model_validate(open_entry) if open_entry else None,
    )


def _log(db, entry_id, edited_by, field, old, new, reason):
    db.add(
        EntryAuditLog(
            entry_id=entry_id,
            edited_by=edited_by,
            field=field,
            old_value=None if old is None else str(old),
            new_value=None if new is None else str(new),
            reason=reason,
        )
    )


@router.patch("/me/entries/{entry_id}", response_model=TimeEntryOut)
def correct_my_entry(
    entry_id: str,
    body: EntryPatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Fix a mistake in one of your own entries (e.g. a forgotten clock-out).
    Every changed field is written to the audit log, and hours/pay are
    recalculated so the stored totals stay consistent."""
    entry = db.get(TimeEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    changed = False
    for field in ("clock_in_at", "clock_out_at", "status", "notes"):
        new_val = getattr(body, field)
        if new_val is not None:
            old_val = getattr(entry, field)
            if old_val != new_val:
                _log(db, entry.id, user.id, field, old_val, new_val, body.reason)
                setattr(entry, field, new_val)
                changed = True

    if changed:
        entry.edited_by = user.id
        # Recompute totals when we have a complete, closed shift.
        if entry.status == "closed" and entry.clock_in_at and entry.clock_out_at:
            result = calculate_shift(entry.clock_in_at, entry.clock_out_at, user.hourly_rate)
            entry.total_minutes = result.total_minutes
            entry.total_pay = result.total_pay
        elif entry.status in ("open", "flagged"):
            entry.total_minutes = None
            entry.total_pay = None

    db.commit()
    db.refresh(entry)
    return TimeEntryOut.model_validate(entry)


@router.get("/me/export")
def export_csv(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    format: str = Query(default="csv"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Payroll-ready CSV of your own shifts. Only closed entries contribute to
    pay; flagged/open rows are included but marked so nothing is silently
    dropped."""
    if format != "csv":
        raise HTTPException(status_code=400, detail="Only csv format is supported")

    stmt = select(TimeEntry).where(TimeEntry.user_id == user.id)
    if from_:
        stmt = stmt.where(TimeEntry.clock_in_at >= from_)
    if to:
        stmt = stmt.where(TimeEntry.clock_in_at < to)
    stmt = stmt.order_by(TimeEntry.clock_in_at)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["Clock In (UTC)", "Clock Out (UTC)", "Hours", "Hourly Rate", "Gross Pay", "Status"]
    )
    for e in db.scalars(stmt):
        hours = round((e.total_minutes or 0) / 60, 2) if e.status == "closed" else ""
        pay = f"{e.total_pay:.2f}" if e.status == "closed" and e.total_pay is not None else ""
        writer.writerow(
            [
                e.clock_in_at.isoformat(),
                e.clock_out_at.isoformat() if e.clock_out_at else "",
                hours,
                f"{user.hourly_rate:.2f}",
                pay,
                e.status,
            ]
        )

    buf.seek(0)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="timesheet_{ts}.csv"'},
    )
