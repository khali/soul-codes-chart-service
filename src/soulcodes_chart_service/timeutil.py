"""Local birth date and clock time to a UTC instant, with daylight saving edge cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo


@dataclass
class ResolvedMoment:
    local: datetime
    utc: datetime
    warnings: list[str] = field(default_factory=list)


def _is_ambiguous(naive: datetime, zone: ZoneInfo) -> bool:
    first = naive.replace(tzinfo=zone, fold=0)
    second = naive.replace(tzinfo=zone, fold=1)
    return first.utcoffset() != second.utcoffset() and _exists(first) and _exists(second)


def _exists(aware: datetime) -> bool:
    round_trip = aware.astimezone(UTC).astimezone(aware.tzinfo)
    return round_trip.replace(tzinfo=None) == aware.replace(tzinfo=None, fold=0)


def resolve_local_time(local_date: date, clock: time, zone: ZoneInfo) -> ResolvedMoment:
    """Convert a wall-clock birth time to UTC, flagging repeated or skipped clock times."""
    naive = datetime.combine(local_date, clock)
    aware = naive.replace(tzinfo=zone, fold=0)
    warnings: list[str] = []
    hhmm = clock.strftime("%H:%M")

    if _is_ambiguous(naive, zone):
        warnings.append(
            f"The clock time {hhmm} happened twice on this date because the clocks went "
            "back; the first occurrence is used."
        )
    elif not _exists(aware):
        shifted = aware.astimezone(UTC).astimezone(zone)
        warnings.append(
            f"The clock time {hhmm} did not exist on this date because the clocks went "
            f"forward; it is read as {shifted:%H:%M}."
        )
        aware = shifted

    return ResolvedMoment(local=aware, utc=aware.astimezone(UTC), warnings=warnings)
