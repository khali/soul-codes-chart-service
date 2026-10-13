"""Concurrent requests must not corrupt each other through Swiss Ephemeris global state."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from soulcodes_chart_service.chart import build_chart
from soulcodes_chart_service.geo.resolver import Location
from soulcodes_chart_service.models import ChartRequest

from .conftest import AMARA_REQUEST, SAMPLE_REQUEST

SYDNEY = Location(-33.86785, 151.20732, "Australia/Sydney")
WELLINGTON = Location(-41.28664, 174.77557, "Pacific/Auckland")


def _chart(job: tuple[dict, Location]) -> dict:
    request, location = job
    payload = build_chart(ChartRequest.model_validate(request), location)
    return payload.model_dump(by_alias=True, mode="json", exclude={"meta": {"calculated_at"}})


def test_parallel_charts_match_serial_results() -> None:
    jobs = [(SAMPLE_REQUEST, SYDNEY), (AMARA_REQUEST, WELLINGTON)] * 8
    expected = [_chart(job) for job in jobs[:2]]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_chart, jobs))
    for index, result in enumerate(results):
        assert result == expected[index % 2]
