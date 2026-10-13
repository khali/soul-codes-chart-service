"""Request and response models. Response field aliases match packages/chart-types exactly.

Attributes are snake_case in Python; JSON keys are camelCase (`bigThree`, `utcDateTime`).
tests/test_contract.py checks every interface in packages/chart-types/src/index.ts
against these models, so a drift on either side fails the build.
"""

from __future__ import annotations

import re
from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from .tz import canonical_zone_name

# Chiron (seas_18.se1, via Kerykeion with speeds) is available from 1800-01-01 01:20 UT to
# 2399-12-31 23:50 UT. The accepted local dates leave room for every UTC offset in the
# time zone database (local mean time reached about -16 and +15 hours) and for the
# whole-day check made when the birth time is unknown.
EARLIEST_DATE = Date(1801, 1, 1)
LATEST_DATE = Date(2399, 12, 30)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

ZodiacSign = Literal[
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]  # fmt: skip
PlanetKey = Literal[
    "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
    "uranus", "neptune", "pluto", "north_node", "south_node", "chiron",
]  # fmt: skip
AspectBody = Literal[
    "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
    "pluto", "north_node", "south_node", "chiron", "ascendant", "midheaven",
]  # fmt: skip
AspectType = Literal["conjunction", "opposition", "trine", "square", "sextile"]
HdCenter = Literal["head", "ajna", "throat", "g", "heart", "sacral", "solar_plexus", "spleen", "root"]
HdPlanet = Literal[
    "sun", "earth", "moon", "north_node", "south_node", "mercury", "venus",
    "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
]  # fmt: skip
HdType = Literal["Generator", "Manifesting Generator", "Projector", "Manifestor", "Reflector"]


class ChartRequest(BaseModel):
    """POST /v1/chart body."""

    name: str = Field(min_length=1, max_length=100)
    date: Date
    time: str | None = None
    place: str = Field(min_length=1, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=64)
    # Refuse (422 place_ambiguous) instead of guessing when `place` is a bare name that other
    # countries share. Off by default: a person reviewing the chart can read the warning.
    reject_ambiguous_place: bool = Field(default=False, alias="rejectAmbiguousPlace")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("name", "place")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()

    @field_validator("date", mode="before")
    @classmethod
    def _iso_date(cls, value: object) -> object:
        if not isinstance(value, str) or not _DATE.match(value):
            raise ValueError("must be a date written as YYYY-MM-DD")
        return value

    @field_validator("date")
    @classmethod
    def _date_range(cls, value: Date) -> Date:
        if not EARLIEST_DATE <= value <= LATEST_DATE:
            raise ValueError("must be between 1801-01-01 and 2399-12-30")
        return value

    @field_validator("time")
    @classmethod
    def _clock_time(cls, value: str | None) -> str | None:
        if value is not None and not _TIME.match(value):
            raise ValueError("must be a 24-hour time written as HH:MM, or null if unknown")
        return value

    @field_validator("timezone")
    @classmethod
    def _iana_zone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        canonical = canonical_zone_name(value)
        if canonical is None:
            raise ValueError("must be an IANA time zone such as 'Australia/Sydney'")
        return canonical

    @model_validator(mode="after")
    def _coordinates_together(self) -> ChartRequest:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be given together")
        return self


class ContractModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class BirthData(ContractModel):
    name: str
    date: str
    time: str | None
    time_known: bool
    place: str
    latitude: float
    longitude: float
    timezone: str
    utc_date_time: str


class SignPlacement(ContractModel):
    sign: ZodiacSign
    degree: float = Field(ge=0, lt=30)
    longitude: float = Field(ge=0, lt=360)


class PlanetPlacement(ContractModel):
    """SignPlacement plus key, house and retrograde (TypeScript: `extends SignPlacement`)."""

    key: PlanetKey
    sign: ZodiacSign
    degree: float = Field(ge=0, lt=30)
    longitude: float = Field(ge=0, lt=360)
    house: int | None = Field(ge=1, le=12)
    retrograde: bool


class HouseCusp(ContractModel):
    number: int = Field(ge=1, le=12)
    sign: ZodiacSign
    longitude: float = Field(ge=0, lt=360)


class Aspect(ContractModel):
    a: AspectBody
    b: AspectBody
    type: AspectType
    orb: float = Field(ge=0)


class BigThree(ContractModel):
    sun: SignPlacement
    moon: SignPlacement
    ascendant: SignPlacement | None


class Angles(ContractModel):
    ascendant: float
    midheaven: float


class AstrologyChart(ContractModel):
    zodiac: Literal["tropical"]
    house_system: Literal["placidus", "whole_sign"]
    big_three: BigThree
    planets: list[PlanetPlacement]
    houses: list[HouseCusp] | None
    angles: Angles | None
    aspects: list[Aspect]


class HdActivation(ContractModel):
    planet: HdPlanet
    gate: int = Field(ge=1, le=64)
    line: int = Field(ge=1, le=6)


class HdChannel(ContractModel):
    gates: tuple[int, int]
    name: str
    centers: tuple[HdCenter, HdCenter]


class HdActivations(ContractModel):
    personality: list[HdActivation]
    design: list[HdActivation]


class HumanDesignChart(ContractModel):
    type: HdType
    strategy: str
    authority: str
    profile: str
    definition: str
    incarnation_cross: str
    signature: str
    not_self_theme: str
    defined_centers: list[HdCenter]
    channels: list[HdChannel]
    activations: HdActivations


class Meta(ContractModel):
    calculated_at: str
    engines: dict[str, str]
    warnings: list[str]


class ChartPayload(ContractModel):
    version: Literal[1]
    birth: BirthData
    astrology: AstrologyChart
    human_design: HumanDesignChart | None
    meta: Meta


class HealthResponse(BaseModel):
    status: Literal["ok"]
    engines: dict[str, str]
