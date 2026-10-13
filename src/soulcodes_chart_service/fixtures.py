"""Regenerate the shared chart fixtures used by the other front-door packages.

    uv run python -m soulcodes_chart_service.fixtures ../../packages/chart-types/fixtures

Uses the real offline geocoder, exactly as the service does. `calculatedAt` is fixed
so the files only change when the calculation (or an engine version) changes.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .chart import build_chart
from .geo.offline import OfflineGeocoder
from .geo.resolver import OfflineTimezoneLookup, resolve_location
from .models import ChartRequest

FIXED_CALCULATED_AT = datetime(2026, 10, 13, tzinfo=UTC)

FIXTURE_REQUESTS: dict[str, dict[str, Any]] = {
    "sample-person.chart.json": {
        "name": "Sample Person",
        "date": "1985-07-04",
        "time": "15:00",
        "place": "Melbourne, Australia",
    },
    # A made-up person whose birth time is unknown.
    "unknown-time.chart.json": {
        "name": "Amara",
        "date": "1988-03-14",
        "time": None,
        "place": "Wellington, New Zealand",
    },
}


def render(filename: str, geocoder: OfflineGeocoder) -> dict[str, Any]:
    request = ChartRequest.model_validate(FIXTURE_REQUESTS[filename])
    location = resolve_location(
        request.place,
        request.latitude,
        request.longitude,
        request.timezone,
        geocoder,
        OfflineTimezoneLookup(),
    )
    chart = build_chart(request, location, now=FIXED_CALCULATED_AT)
    return chart.model_dump(by_alias=True, mode="json")


def to_json(chart: dict[str, Any]) -> str:
    return json.dumps(chart, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    out_dir = Path(argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    geocoder = OfflineGeocoder()
    for filename in FIXTURE_REQUESTS:
        (out_dir / filename).write_text(to_json(render(filename, geocoder)), encoding="utf-8")
        print(f"wrote {out_dir / filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
