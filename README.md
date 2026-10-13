# Soul Codes chart service

A stateless HTTP service that turns a birth date, time and place into a `ChartPayload`:
a tropical astrology chart and a Human Design chart. It is the calculation layer of the
soulcodes.ai front door (see `docs/door/CONTRACT.md`). The response shape is defined by
`packages/chart-types/src/index.ts` and the keys match it exactly (camelCase).

The service keeps nothing: no database, no files written, no calls to other services.
Geocoding and time zone lookup use data bundled with the Python packages.

## Run it

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11.

```bash
cd services/chart-service
uv sync

# Local development without auth (never in production):
CHART_SERVICE_ALLOW_NO_AUTH=1 uv run uvicorn soulcodes_chart_service.app:create_app --factory --port 8080

# With auth, as in production:
export CHART_SERVICE_TOKEN="$(openssl rand -hex 32)"
uv run uvicorn soulcodes_chart_service.app:create_app --factory --port 8080
```

```bash
curl -s localhost:8080/v1/chart \
  -H "Authorization: Bearer $CHART_SERVICE_TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Amara","date":"1988-03-14","time":null,"place":"Wellington, New Zealand"}'
```

The geocoder index loads at startup: about 4 seconds, and the whole process then uses
about 195 MB of memory (see `CHART_SERVICE_GEO_MIN_POPULATION`).

### Docker

```bash
docker build -t soulcodes-chart-service services/chart-service
docker run --rm -p 8080:8080 -e CHART_SERVICE_TOKEN="$(openssl rand -hex 32)" soulcodes-chart-service
```

Slim Python 3.11 image, runs as an unprivileged user (uid 10001), one worker, with a
`HEALTHCHECK` against `/healthz`. Scale by running more containers rather than more
workers: calculations are serialised inside a process (see "Concurrency").

## Environment variables

| Variable | Required | Meaning |
|---|---|---|
| `CHART_SERVICE_TOKEN` | Yes | Bearer token callers must send. At least 32 characters. The service refuses to start without it. |
| `CHART_SERVICE_ALLOW_NO_AUTH` | No | Set to exactly `1` to run without a token. Local development only; logs a warning. |
| `CHART_SERVICE_GEO_MIN_POPULATION` | No | Smallest town the geocoder knows: `500`, `1000`, `5000` (default) or `15000`. Process memory after start: about 125 MB at `15000`, 195 MB at `5000`, 365 MB at `1000`. |

## API

### `GET /healthz`

No auth. Returns `{"status": "ok", "engines": {...}}` with the same engine versions as
`meta.engines`.

### `POST /v1/chart`

Header `Authorization: Bearer <CHART_SERVICE_TOKEN>` (compared in constant time).

| Field | Type | Notes |
|---|---|---|
| `name` | string, 1 to 100 chars | Echoed back in `birth.name`. |
| `date` | `"YYYY-MM-DD"` | Local date at the birthplace. 1801-01-01 to 2399-12-30 (inside the range of the Chiron ephemeris at every UTC offset). |
| `time` | `"HH:MM"` or `null` | Local 24-hour clock time. `null` means unknown. |
| `place` | string, 1 to 200 chars | Geocoded when coordinates are missing; always echoed back. |
| `latitude`, `longitude` | number or `null` | Must be given together. When given, they win over `place`. |
| `timezone` | IANA name or `null` | e.g. `"Australia/Sydney"` (case-insensitive). When given, it wins. Otherwise taken from the geocoded place, or looked up from the coordinates. |
| `rejectAmbiguousPlace` | boolean, default `false` | When `true`, a bare place name that other countries share ("Wellington") is refused with `place_ambiguous` instead of being guessed with a warning. For callers with nobody to check the guess, such as the door's self-serve form. |

Response: a `ChartPayload` (the models are in `src/soulcodes_chart_service/models.py`).

Errors always look like `{"error": {"code": "...", "message": "..."}}`:

| Status | `code` | When |
|---|---|---|
| 400 | `bad_request` | Body is not valid JSON. |
| 401 | `unauthorized` | Missing or wrong bearer token. |
| 404 / 405 | `not_found` / `method_not_allowed` | Unknown route or method. |
| 422 | `invalid_request` | A field failed validation; the message names it. |
| 422 | `place_not_found` | The place could not be geocoded. Send coordinates and a time zone instead. |
| 422 | `place_ambiguous` | Only with `rejectAmbiguousPlace`: more than one country has a place of that name. Add the country, or send coordinates. |
| 422 | `timezone_not_found` | No time zone for the coordinates (for example, mid-ocean). Send `timezone`. |
| 500 | `internal_error` | Anything unexpected. Details go to the log, never to the caller. |

`meta.warnings` holds plain-English notes for the reader (British English), for example
an unknown birth time, an ambiguous place name, a clock time repeated or skipped by a
daylight saving change, or results that would change with a slightly different time.

## How charts are calculated

**Time.** The local date and clock time are converted to UTC with the IANA time zone
database from the pinned `tzdata` package, never the host's zone files, so historical
daylight saving rules are identical everywhere. A clock time that happened twice (clocks
went back) uses the first occurrence; one that never happened (clocks went forward) is
moved forward by the gap. Both add a warning.

**Ephemeris.** Swiss Ephemeris via pyswisseph. Planets and the Moon use its built-in
Moshier routines (no large data files; accurate to a few arc-seconds or better in this
date range, far finer than a Human Design line of 56 arc-minutes); Chiron uses the `seas_18.se1` file shipped with Kerykeion. Kerykeion and the
Human Design engine therefore see exactly the same planet positions (a test checks this).

**Astrology.** Tropical zodiac, apparent geocentric positions, true lunar node (the South
Node is opposite). Planets: Sun to Pluto, North and South Node, Chiron. Positions are
rounded to 4 decimal places.

**Houses.** Placidus, calculated with pyswisseph at the true latitude. Kerykeion clamps
latitude to 66 degrees for every house system, which would silently move the Ascendant
of anyone born further north or south, so its houses are not used. Beyond 66 degrees
(or if Placidus fails) whole sign houses are used, with a warning.

**Aspects.** Conjunction, opposition, trine, square and sextile, among the planets and
the Ascendant and Midheaven, listed tightest first. For a pair, the smaller of the two
allowances applies:

| Class | Conjunction | Opposition | Trine | Square | Sextile |
|---|---|---|---|---|---|
| Sun, Moon | 10 | 10 | 8 | 8 | 6 |
| Mercury to Pluto | 8 | 8 | 7 | 7 | 5 |
| Ascendant, Midheaven | 8 | 8 | 6 | 6 | 4 |
| Nodes, Chiron | 5 | 5 | 4 | 4 | 3 |

North Node with South Node, and Ascendant with Midheaven, are skipped (always in aspect).

**Unknown birth time.** Positions are calculated for 12:00 local time. Houses, angles,
the Ascendant and planet houses are `null`, and aspects involve planets only.
`humanDesign` is `null`. Warnings say so, and say whether the Moon (or any other body)
changed sign that day, so the reading can hold it lightly.

**Time sensitivity.** For a known time, the chart is also checked 15 minutes either
side. If the sign of any planet or of the Ascendant, or the Human Design type,
authority, profile, definition or incarnation cross would change, a warning says which.

**Geocoding.** Offline, from the GeoNames city lists bundled in `geonamescache`
(towns of 5,000 people or more by default). It understands "City, Country",
"City, State, Country", postcodes ("Hornsby NSW 2077, Australia"), accents
("Sao Paulo"), alternative names ("Bombay"), US states and Australian, Canadian and UK
regions, and two-letter state codes that clash with country codes ("Portland, ME").
With no country, the most populous match wins and a warning names the country used.
Time zones for bare coordinates come from `timezonefinder`. The geocoder sits behind a
small interface (`geo.resolver.Geocoder`), so an online geocoder could be added later
without touching the rest; none is used now.

## Human Design engine

The maths comes from the project's own engine, **the private soul-codes-hd repository at
`46ff24d5806e545ea136277a021dce9a02215550`**, vendored (copied) into
`src/soulcodes_chart_service/vendor/soulcodes_hd/`. It is not a git dependency because
that package declares Supabase, PostgREST, OpenAI, Flask, SQLAlchemy, psycopg2, SendGrid
and more as hard dependencies, and its engine imports geopy (online Nominatim lookups)
and a 9,400-line reference data module at import time. Only pure modules were copied:
the gate wheel, planet positions and design-date search, incarnation cross tables, the
channel and gate maps, and channel names. Every file's header records its source and any
change. Changes to upstream behaviour:

- Gate 51's right angle cross was listed as "Penetration 2" (the same as gate 53); it is
  "Penetration". Found by a structural test over all cross families.
- A longitude of exactly 302.0 degrees crashed upstream (index out of range); fixed.
- A failed planet calculation returned 0.0 silently upstream; it now raises.
- British spelling in two juxtaposition cross names ("Behaviour", and "Possession" typo).

Type, authority and definition are reimplemented in `hd/analysis.py`, using connected
groups of centres, because upstream: only counted a motor as reaching the Throat through
a direct channel (so Sacral to G to Throat was called a Generator, not a Manifesting
Generator); mapped channel 27-50 to Sacral/Root in its definition table; and gave
Reflectors "Mental" authority instead of Lunar.

**Validation.** In the private repository the engine is checked against independent
reference charts (gate and line for every activation, design time, type, profile,
authority, definition, cross). Those charts are real people's birth data, so that test
is not part of this public tree. The tests here pin a fictional "Sample Person" chart
(`tests/test_sample_chart.py`) and the gate wheel, so they catch unintended changes but
are not an independent oracle.

Authority labels: `Emotional (Solar Plexus)`, `Sacral`, `Splenic`, `Ego Manifested`,
`Ego Projected`, `Self-Projected`, `Mental`, `Lunar`. Definition labels:
`Single Definition`, `Split Definition`, `Triple Split Definition`,
`Quadruple Split Definition`, `No Definition`. Right angle crosses carry their quarter
number from the second quarter on ("Right Angle Cross of Eden 2"), following HDKit.

## Concurrency

The Swiss Ephemeris C library keeps global state and is not thread-safe. FastAPI runs the
chart endpoint in a thread pool, so every calculation holds one process-wide lock. A
chart takes about 10 ms of calculation, so one worker handles roughly 100 charts a second.

## Tests

```bash
cd services/chart-service
uv run pytest            # about 5 seconds, no network (sockets are blocked)
uv run ruff check src tests && uv run ruff format --check src tests
```

Two test files that need the private monorepo (a check against the TypeScript contract
and a cross-check against private reference charts) are not part of this tree.

## Fixtures

`sample-person.chart.json` and `unknown-time.chart.json` (a fictional person born
1985-07-04 in Melbourne, and Amara, a made-up person with an unknown birth time) are
produced by this service. Regenerate them into any directory with:

```bash
uv run python -m soulcodes_chart_service.fixtures ./fixtures
```

## Licences

Runtime dependencies, with licence strings as recorded in each package's metadata
(Python 3.11 lock). Build-time and test-only tools are not shipped in the image.

| Package | Version | Licence (metadata) |
|---|---|---|
| **kerykeion** | 5.12.10 | **AGPL-3.0** (License field; its classifier says GPLv3) |
| **pyswisseph** (Swiss Ephemeris) | 2.10.3.2 | **GNU Affero General Public License v3** (classifier); Swiss Ephemeris is dual-licensed AGPL or Astrodienst commercial licence |
| geonamescache | 3.0.2 | MIT (bundled GeoNames data: CC BY 4.0, attribution required) |
| timezonefinder | 9.0.0 | The MIT License (MIT) |
| timezonefinder-data | 3.2026.3.post1 | Open Database License (ODbL) v1.0 |
| tzdata | 2026.5 | Apache-2.0 (IANA tz data is public domain) |
| fastapi | 0.143.0 | MIT |
| starlette | 1.7.0 | BSD-3-Clause |
| pydantic / pydantic-core | 2.14.1 / 2.50.1 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |
| uvloop | 0.23.0 | MIT License (classifiers: Apache, MIT) |
| httptools | 0.9.0 | MIT |
| h11 | 0.16.0 | MIT |
| websockets | 17.2 | BSD-3-Clause |
| watchfiles | 1.3.0 | MIT |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| pyyaml | 6.0.3 | MIT |
| click | 8.5.0 | BSD-3-Clause |
| anyio | 4.15.1 | MIT |
| idna | 3.20 | BSD-3-Clause |
| annotated-types / annotated-doc | 0.8.0 / 0.0.5 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |
| numpy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| h3 | 4.5.0 | Apache License |
| flatbuffers | 25.12.19 | Apache 2.0 |
| cffi / pycparser | 2.1.1 / 3.11 | MIT-0 / BSD-3-Clause |
| pytz | 2026.5 | MIT |
| requests | 2.34.2 | Apache-2.0 |
| requests-cache | 1.3.3 | BSD-2-Clause |
| urllib3 | 2.8.0 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| charset-normalizer | 3.5.2 | MIT |
| attrs / cattrs | 26.1.0 / 26.2.1 | MIT |
| platformdirs | 4.13.0 | MIT |
| url-normalize | 3.0.1 | MIT |
| scour | 0.38.2 | Apache License 2.0 |
| simple-ascii-tables | 1.0.1 | MIT (classifiers also list GPL) |
| six | 1.17.0 | MIT |
| opentelemetry-api | 1.45.1 | Apache-2.0 |
| soulcodes-hd (vendored subset) | 46ff24d5 | Original code by this project's author; no licence file upstream |

**Attention:** Kerykeion and the Swiss Ephemeris are AGPL. Running AGPL code as a network
service generally obliges you to offer its source, including your changes, to the people
who use it over the network. Before public launch, decide between publishing this
service's source under the AGPL or buying a Swiss Ephemeris professional licence from
Astrodienst and replacing Kerykeion. GeoNames (CC BY 4.0) and timezonefinder-data (ODbL)
ask for attribution. This is a flag, not legal advice.

## Known limitations

- Places smaller than the population threshold are not found; the caller can send
  coordinates and a time zone instead.
- Time zone history before 1970 in the IANA database is reliable for most places but
  not all; local mean time is used before standard time was adopted.
- Kerykeion is held below version 6, which replaces the Swiss Ephemeris. Raising it
  needs the reference tests re-run and the fixtures regenerated.
