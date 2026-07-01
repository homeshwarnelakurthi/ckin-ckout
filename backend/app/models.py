"""SQLAlchemy models for the single-user time tracker.

Design notes:
- All timestamps are timezone-aware and stored in UTC.
- A partial unique index guarantees at most one open shift at a time, at the
  DB level, backing up the application-layer check.
- entry_audit_log keeps the full edit trail so a correction never silently
  overwrites the original figures.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import GUID, Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    hourly_rate: Mapped[float] = mapped_column(
        Numeric(6, 2), nullable=False, server_default=text("10.00")
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    entries: Mapped[list["TimeEntry"]] = relationship(
        back_populates="user", foreign_keys="TimeEntry.user_id"
    )


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id"), nullable=False
    )
    clock_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    clock_out_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_pay: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    edited_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    user: Mapped["User"] = relationship(back_populates="entries", foreign_keys=[user_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('open','closed','flagged')", name="ck_time_entries_status"
        ),
        # Fast per-user history + reporting lookups.
        Index("ix_time_entries_user_clockin", "user_id", "clock_in_at"),
        # At most one OPEN shift per user, enforced by the database.
        Index(
            "uq_one_open_entry_per_user",
            "user_id",
            unique=True,
            sqlite_where=text("status = 'open'"),
            postgresql_where=text("status = 'open'"),
        ),
    )


class EntryAuditLog(Base):
    """Append-only record of admin corrections to time entries."""

    __tablename__ = "entry_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("time_entries.id"), nullable=False, index=True
    )
    edited_by: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id"), nullable=False
    )
    # JSON-ish text snapshots of the fields before/after the change.
    field: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
