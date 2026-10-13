"""Local time to UTC, including daylight saving edge cases, and time zone loading."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

import pytest

from soulcodes_chart_service.timeutil import resolve_local_time
from soulcodes_chart_service.tz import canonical_zone_name, load_zone

SYDNEY = load_zone("Australia/Sydney")


def test_standard_time() -> None:
    moment = resolve_local_time(date(1985, 7, 4), time(15, 0), SYDNEY)
    assert moment.utc == datetime(1985, 7, 4, 5, 0, tzinfo=UTC)
    assert moment.warnings == []


def test_summer_time() -> None:
    moment = resolve_local_time(date(1985, 1, 10), time(12, 0), SYDNEY)
    assert moment.utc == datetime(1985, 1, 10, 1, 0, tzinfo=UTC)


def test_repeated_clock_time_uses_first_occurrence() -> None:
    # Sydney clocks went back from 03:00 to 02:00 on 4 April 2021.
    moment = resolve_local_time(date(2021, 4, 4), time(2, 30), SYDNEY)
    assert moment.utc == datetime(2021, 4, 3, 15, 30, tzinfo=UTC)  # still on UTC+11
    assert moment.warnings == [
        "The clock time 02:30 happened twice on this date because the clocks went back; "
        "the first occurrence is used."
    ]


def test_skipped_clock_time_is_moved_forward() -> None:
    # Sydney clocks went forward from 02:00 to 03:00 on 3 October 2021.
    moment = resolve_local_time(date(2021, 10, 3), time(2, 30), SYDNEY)
    assert moment.utc == datetime(2021, 10, 2, 16, 30, tzinfo=UTC)
    assert moment.local.strftime("%H:%M") == "03:30"
    assert moment.warnings == [
        "The clock time 02:30 did not exist on this date because the clocks went forward; "
        "it is read as 03:30."
    ]


def test_zone_names_are_case_insensitive_and_canonical() -> None:
    assert canonical_zone_name("australia/sydney") == "Australia/Sydney"
    assert canonical_zone_name("Mars/Olympus_Mons") is None
    assert load_zone("PACIFIC/AUCKLAND").key == "Pacific/Auckland"
    with pytest.raises(KeyError):
        load_zone("Nowhere/Special")
