"""Isolated, unit-tested hours & pay calculation.

Deliberately free of any database, framework, or I/O dependency so it can be
tested in isolation and reused anywhere. Everything is driven by explicit
arguments; `hourly_rate` is passed in (from users.hourly_rate or config) rather
than hardcoded, so a future rate change or overtime tier can be layered on
without rewriting callers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal


def _as_utc(dt: datetime) -> datetime:
    """Normalize to UTC. Naive datetimes are assumed to already be UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_minutes(clock_in_at: datetime, clock_out_at: datetime) -> int:
    """Whole minutes between two instants (rounded to nearest minute).

    Works transparently across midnight and DST boundaries because the math is
    done on UTC instants, not wall-clock times.
    """
    start = _as_utc(clock_in_at)
    end = _as_utc(clock_out_at)
    seconds = (end - start).total_seconds()
    if seconds < 0:
        raise ValueError("clock_out_at must be at or after clock_in_at")
    return round(seconds / 60)


def compute_pay(total_minutes: int, hourly_rate: float | Decimal) -> Decimal:
    """Pay for a number of minutes at the given hourly rate, to the cent."""
    if total_minutes < 0:
        raise ValueError("total_minutes cannot be negative")
    hours = Decimal(total_minutes) / Decimal(60)
    rate = Decimal(str(hourly_rate))
    return (hours * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ShiftResult:
    total_minutes: int
    total_hours: float
    total_pay: Decimal


def calculate_shift(
    clock_in_at: datetime,
    clock_out_at: datetime,
    hourly_rate: float | Decimal,
) -> ShiftResult:
    """Full calculation for one closed shift."""
    minutes = compute_minutes(clock_in_at, clock_out_at)
    pay = compute_pay(minutes, hourly_rate)
    return ShiftResult(
        total_minutes=minutes,
        total_hours=round(minutes / 60, 2),
        total_pay=pay,
    )


def is_over_threshold(
    clock_in_at: datetime, now: datetime, threshold_hours: int
) -> bool:
    """True if an open shift has run past the auto-flag threshold."""
    elapsed = (_as_utc(now) - _as_utc(clock_in_at)).total_seconds() / 3600
    return elapsed > threshold_hours


@dataclass(frozen=True)
class PeriodTotals:
    total_minutes: int
    total_hours: float
    total_pay: Decimal


def aggregate(entries: list[dict]) -> PeriodTotals:
    """Sum a collection of closed entries into period totals.

    Each entry is a mapping with at least ``status``, ``total_minutes`` and
    ``total_pay``. Entries that are not ``closed`` (i.e. still open or flagged
    for review) are excluded from totals — a forgotten clock-out must never
    inflate or corrupt a pay figure.
    """
    total_minutes = 0
    total_pay = Decimal("0.00")
    for e in entries:
        if e.get("status") != "closed":
            continue
        total_minutes += int(e.get("total_minutes") or 0)
        total_pay += Decimal(str(e.get("total_pay") or "0"))
    return PeriodTotals(
        total_minutes=total_minutes,
        total_hours=round(total_minutes / 60, 2),
        total_pay=total_pay.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    )
