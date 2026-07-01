"""Unit tests for the isolated payroll calculator.

Covers the spec's required edge cases:
- multiple shifts in a single calendar day (summed),
- a shift that crosses midnight,
- a forgotten clock-out (flagged, excluded from totals).
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.payroll_calculator import (
    aggregate,
    calculate_shift,
    compute_minutes,
    compute_pay,
    is_over_threshold,
)

UTC = timezone.utc


def dt(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=UTC)


def test_basic_shift_8_hours():
    r = calculate_shift(dt(2026, 7, 1, 9), dt(2026, 7, 1, 17), 10.00)
    assert r.total_minutes == 480
    assert r.total_hours == 8.0
    assert r.total_pay == Decimal("80.00")


def test_partial_hour_rounding():
    # 9:00 -> 9:37 = 37 minutes at $10/hr.
    r = calculate_shift(dt(2026, 7, 1, 9, 0), dt(2026, 7, 1, 9, 37), 10.00)
    assert r.total_minutes == 37
    assert r.total_pay == Decimal("6.17")  # 37/60*10 = 6.1666.. -> 6.17


def test_shift_crossing_midnight():
    # 22:00 -> 06:00 next day = 8 hours.
    r = calculate_shift(dt(2026, 7, 1, 22), dt(2026, 7, 2, 6), 10.00)
    assert r.total_minutes == 480
    assert r.total_pay == Decimal("80.00")


def test_multiple_shifts_single_day_sum():
    e1 = calculate_shift(dt(2026, 7, 1, 8), dt(2026, 7, 1, 12), 10.00)
    e2 = calculate_shift(dt(2026, 7, 1, 13), dt(2026, 7, 1, 17), 10.00)
    totals = aggregate(
        [
            {"status": "closed", "total_minutes": e1.total_minutes, "total_pay": e1.total_pay},
            {"status": "closed", "total_minutes": e2.total_minutes, "total_pay": e2.total_pay},
        ]
    )
    assert totals.total_minutes == 480
    assert totals.total_hours == 8.0
    assert totals.total_pay == Decimal("80.00")


def test_flagged_and_open_excluded_from_totals():
    totals = aggregate(
        [
            {"status": "closed", "total_minutes": 240, "total_pay": Decimal("40.00")},
            {"status": "flagged", "total_minutes": None, "total_pay": None},
            {"status": "open", "total_minutes": None, "total_pay": None},
        ]
    )
    # Only the closed 4h entry counts.
    assert totals.total_minutes == 240
    assert totals.total_pay == Decimal("40.00")


def test_forgotten_clockout_over_threshold():
    clock_in = dt(2026, 7, 1, 8)
    now = clock_in + timedelta(hours=15)
    assert is_over_threshold(clock_in, now, threshold_hours=14) is True
    assert is_over_threshold(clock_in, clock_in + timedelta(hours=13), 14) is False


def test_configurable_rate():
    r = calculate_shift(dt(2026, 7, 1, 9), dt(2026, 7, 1, 17), Decimal("15.50"))
    assert r.total_pay == Decimal("124.00")  # 8 * 15.50


def test_naive_datetime_treated_as_utc():
    naive_in = datetime(2026, 7, 1, 9)
    naive_out = datetime(2026, 7, 1, 17)
    assert compute_minutes(naive_in, naive_out) == 480


def test_negative_duration_rejected():
    with pytest.raises(ValueError):
        compute_minutes(dt(2026, 7, 1, 17), dt(2026, 7, 1, 9))


def test_compute_pay_zero_minutes():
    assert compute_pay(0, 10.00) == Decimal("0.00")
