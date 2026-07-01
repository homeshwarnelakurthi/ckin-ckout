"""Seed the database with one user (Hpatel) and sample shifts for local dev.

Run with:  python -m app.seed
Idempotent-ish: it wipes and recreates the sample data each run.
"""
from datetime import datetime, timedelta, timezone

from .config import get_settings
from .database import Base, SessionLocal, engine
from .models import EntryAuditLog, TimeEntry, User
from .payroll_calculator import calculate_shift
from .security import hash_secret

settings = get_settings()


def _closed(user, start, end):
    r = calculate_shift(start, end, user.hourly_rate)
    return TimeEntry(
        user_id=user.id,
        clock_in_at=start,
        clock_out_at=end,
        total_minutes=r.total_minutes,
        total_pay=r.total_pay,
        status="closed",
    )


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Fresh start.
        db.query(EntryAuditLog).delete()
        db.query(TimeEntry).delete()
        db.query(User).delete()
        db.commit()

        user = User(
            full_name=settings.manager_name,
            username="123",
            password_hash=hash_secret("1234"),
            hourly_rate=settings.default_hourly_rate,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        now = datetime.now(timezone.utc)
        today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)

        entries: list[TimeEntry] = [
            # Two shifts in one day (should sum for the daily total).
            _closed(user, today0 + timedelta(hours=8), today0 + timedelta(hours=12)),
            _closed(user, today0 + timedelta(hours=13), today0 + timedelta(hours=17)),
            # A shift that crosses midnight (yesterday 22:00 -> today 06:00).
            _closed(user, today0 - timedelta(hours=2), today0 + timedelta(hours=6)),
            # A normal past shift.
            _closed(
                user,
                today0 - timedelta(days=1, hours=-9),
                today0 - timedelta(days=1, hours=-17),
            ),
            # A forgotten clock-out -> flagged, excluded from pay.
            TimeEntry(
                user_id=user.id,
                clock_in_at=today0 - timedelta(days=2, hours=-8),
                clock_out_at=today0 - timedelta(days=2, hours=-8) + timedelta(hours=20),
                status="flagged",
                notes="Auto-flagged: shift exceeded 14h threshold.",
            ),
        ]

        db.add_all(entries)
        db.commit()

        print("Seed complete.")
        print("  Login: 123 / 1234")
        print(f"  Entries: {db.query(TimeEntry).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
