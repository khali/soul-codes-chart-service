"""Build a ChartPayload from a validated request and a resolved location."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, time
from typing import Any

from .astro import calculator as astro
from .astro.uncertainty import NO_TIME_WARNING, sign_change_warnings
from .engines import engine_versions
from .geo.resolver import Location
from .hd import calculator as hd
from .models import ChartPayload, ChartRequest
from .sensitivity import ascendant_warning, human_design_warning, planet_sign_warnings
from .timeutil import resolve_local_time
from .tz import load_zone

HD_UNKNOWN_TIME_WARNING = (
    "Birth time unknown: the Human Design chart needs the time of birth, so it is not included."
)

# The Swiss Ephemeris C library keeps global state (ephemeris path, caches) and is not
# thread-safe. FastAPI runs sync endpoints in a thread pool, so serialise all use of it.
EPHEMERIS_LOCK = threading.Lock()


def _iso_utc(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _known_time(request: ChartRequest, location: Location) -> tuple[Any, Any, list[str], datetime]:
    zone = load_zone(location.timezone)
    clock = time.fromisoformat(request.time)
    moment = resolve_local_time(request.date, clock, zone)
    lat, lng = location.latitude, location.longitude

    chart = astro.calculate_known_time(moment.utc, lat, lng)
    hd_result = hd.calculate(moment.utc)
    warnings = moment.warnings + chart.warnings + planet_sign_warnings(moment.utc, lat, lng)
    for warning in (ascendant_warning(moment.utc, lat, lng), human_design_warning(moment.utc, hd_result)):
        if warning:
            warnings.append(warning)
    return chart.payload, hd.to_payload(hd_result), warnings, moment.utc


def _unknown_time(request: ChartRequest, location: Location) -> tuple[Any, None, list[str], datetime]:
    zone = load_zone(location.timezone)
    lat, lng = location.latitude, location.longitude
    start, midday, end = (
        resolve_local_time(request.date, clock, zone).utc for clock in (time(0, 0), time(12, 0), time(23, 59))
    )
    chart = astro.calculate_unknown_time(midday, lat, lng)
    day_warnings = sign_change_warnings(
        astro.planet_positions(start, lat, lng),
        astro.planet_positions(midday, lat, lng),
        astro.planet_positions(end, lat, lng),
    )
    warnings = [NO_TIME_WARNING, *day_warnings, HD_UNKNOWN_TIME_WARNING]
    return chart.payload, None, warnings, midday


def build_chart(request: ChartRequest, location: Location, now: datetime | None = None) -> ChartPayload:
    """Calculate the astrology and Human Design chart for one birth."""
    with EPHEMERIS_LOCK:
        if request.time is None:
            astrology, human_design, warnings, moment = _unknown_time(request, location)
        else:
            astrology, human_design, warnings, moment = _known_time(request, location)

    birth = {
        "name": request.name,
        "date": request.date.isoformat(),
        "time": request.time,
        "time_known": request.time is not None,
        "place": request.place,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timezone": location.timezone,
        "utc_date_time": _iso_utc(moment),
    }
    meta = {
        "calculated_at": _iso_utc(now or datetime.now(UTC)),
        "engines": engine_versions(),
        "warnings": location.warnings + warnings,
    }
    return ChartPayload.model_validate(
        {"version": 1, "birth": birth, "astrology": astrology, "human_design": human_design, "meta": meta}
    )
