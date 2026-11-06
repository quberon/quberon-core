"""Direct coverage for app.main:utcnow() (app/main.py:61-62).

utcnow() is the single clock source for session expiry
(Store.create_session) and, via iso(), for state/event/status
timestamps. Its contract is narrow but load-bearing:

    return datetime.now(timezone.utc)

These tests pin that contract without creating an app, touching the
filesystem, or depending on wall-clock exactness: a return value is
bracketed between aware-UTC readings taken immediately before and
after the call. They fail if utcnow() ever regresses to a naive
datetime (e.g. datetime.utcnow()/now() without tz), a non-UTC
offset, or a frozen/cached timestamp.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app.main as main_module
from app.main import utcnow


def test_utcnow_returns_aware_datetime_in_utc():
    result = utcnow()
    assert isinstance(result, datetime)
    # Aware, and specifically UTC: tzinfo present, offset exactly zero.
    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)
    assert result.tzinfo == timezone.utc


def test_utcnow_is_current_not_frozen_or_epoch():
    before = datetime.now(timezone.utc)
    result = utcnow()
    after = datetime.now(timezone.utc)
    assert before <= result <= after


def test_utcnow_is_monotonic_non_decreasing_across_calls():
    first = utcnow()
    second = utcnow()
    assert second >= first
    # Distinct calls track the real clock, not a cached constant far
    # in the past; both must lie inside this test's own time window.
    assert datetime.now(timezone.utc) - second < timedelta(seconds=60)


def test_utcnow_delegates_to_datetime_now_with_timezone_utc(monkeypatch):
    fixed = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    seen = {}

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            seen["tz"] = tz
            return fixed

    monkeypatch.setattr(main_module, "datetime", _FixedDatetime)
    assert utcnow() is fixed
    assert seen["tz"] is timezone.utc


def test_utcnow_isoformat_has_explicit_zero_offset_and_roundtrips():
    result = utcnow()
    text = result.isoformat()
    # e.g. "2026-11-06T12:00:00.123456+00:00" -- never a naive string
    # and never a "Z"/local-offset rendering that downstream string
    # comparisons in Store.get_session would mis-order.
    assert text.endswith("+00:00")
    parsed = datetime.fromisoformat(text)
    assert parsed == result
    assert parsed.utcoffset() == timedelta(0)
