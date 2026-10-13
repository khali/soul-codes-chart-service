# Source for the soulcodes.ai chart service

This is the complete source of the chart calculation service that runs behind
https://soulcodes.ai, published under the GNU Affero General Public License v3 (see LICENSE)
because it uses the Swiss Ephemeris (via pyswisseph) and Kerykeion, both AGPL-3.0.

Exported from the private soul-codes-app repository at commit 286c85e.
Three test files are omitted because they depend on private data: a cross-check of a real
person's chart against an independent reference, a check against private reference charts,
and a check against the private TypeScript contract. The tests use a fictional "Sample Person"
instead; the source code is complete.
Place names: GeoNames (CC BY 4.0). Time zone boundaries: OpenStreetMap contributors (ODbL).
