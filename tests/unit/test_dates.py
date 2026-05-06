"""Long-form English date rendering (research §R5, FR-009).

The rendering must:
- emit hard-coded English month names regardless of system locale,
- omit the leading zero on the day of month,
- use single spaces between day, month, year.
"""

from __future__ import annotations

import locale
from datetime import date

import pytest

from sprint_recap.deck import format_long_date


@pytest.mark.parametrize(
    "input_date, expected",
    [
        (date(2026, 5, 6), "6 May 2026"),
        (date(2026, 12, 12), "12 December 2026"),
        (date(2027, 1, 1), "1 January 2027"),
        (date(2026, 1, 31), "31 January 2026"),
        (date(2026, 9, 9), "9 September 2026"),
    ],
)
def test_format_long_date_examples(input_date: date, expected: str) -> None:
    assert format_long_date(input_date) == expected


def test_format_long_date_no_leading_zero() -> None:
    assert format_long_date(date(2026, 3, 1)).startswith("1 ")
    assert format_long_date(date(2026, 3, 9)).startswith("9 ")
    # Two-digit days are kept as-is (no zero stripping past 9).
    assert format_long_date(date(2026, 3, 10)).startswith("10 ")


def test_format_long_date_locale_independent() -> None:
    """Force a non-English locale where it is available; ensure the output
    is still English. Skip if the locale is unavailable on this system —
    the implementation must not depend on a system locale being installed."""
    try:
        locale.setlocale(locale.LC_TIME, "nb_NO.UTF-8")
    except locale.Error:
        pytest.skip("nb_NO.UTF-8 locale not installed on this system")
    try:
        assert format_long_date(date(2026, 5, 6)) == "6 May 2026"
    finally:
        locale.setlocale(locale.LC_TIME, "C")
