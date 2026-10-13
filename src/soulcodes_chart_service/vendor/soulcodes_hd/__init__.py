"""Minimal pure-calculation subset of the Soul Codes Human Design engine.

Source repository: the private soul-codes-hd repository
Source commit:     46ff24d5806e545ea136277a021dce9a02215550 (2026-10-13 snapshot)

Why vendored rather than a git dependency: the upstream package declares Supabase,
PostgREST, OpenAI, Flask, SQLAlchemy, psycopg2, SendGrid and others as hard
dependencies, and its calculation engine imports geopy (online Nominatim lookups)
and the 9,400-line reference-data module at import time. This service needs none of
that, so only the pure maths and lookup tables are copied here.

Files and what they hold (each file's header lists its exact source and changes):
  exceptions.py        domain exceptions (verbatim)
  center.py            CenterName value object (verbatim, relative import)
  channel_mappings.py  channel -> centres table (verbatim, relative import)
  gate_mappings.py     gate -> centre table (verbatim, relative import)
  channel_names.py     the 36 channel names, extracted from data/reference.py
  wheel.py             gate order and longitude -> gate/line/colour/tone/base
  ephemeris.py         planet longitudes (Moshier, true node) and design-date search
  crosses.py           incarnation cross tables and naming rule

Not vendored, deliberately: type, authority and definition rules. Those are
reimplemented in soulcodes_chart_service.hd.analysis because upstream (a) treats a
motor as reaching the Throat only through a direct channel, (b) maps channel 27-50 to
Sacral/Root in its definition table, and (c) gives Reflectors "Mental" authority.
See the README "Human Design engine" section.
"""

SOURCE_REPOSITORY = "the private soul-codes-hd repository"
SOURCE_COMMIT = "46ff24d5806e545ea136277a021dce9a02215550"
