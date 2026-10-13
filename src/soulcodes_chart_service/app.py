"""FastAPI application: GET /healthz and POST /v1/chart.

Run with `uvicorn soulcodes_chart_service.app:create_app --factory`.
"""

from __future__ import annotations

import hmac
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .chart import build_chart
from .config import Settings, load_settings
from .engines import engine_versions
from .errors import ServiceError, envelope
from .geo.offline import OfflineGeocoder
from .geo.resolver import Geocoder, OfflineTimezoneLookup, TimezoneLookup, resolve_location
from .models import ChartPayload, ChartRequest, HealthResponse

logger = logging.getLogger("soulcodes_chart_service")

_HTTP_CODES = {404: "not_found", 405: "method_not_allowed"}


def _unauthorised() -> ServiceError:
    return ServiceError(401, "unauthorized", "Missing or invalid bearer token.")


def _check_bearer(request: Request) -> None:
    settings: Settings = request.app.state.settings
    if settings.token is None:
        return
    scheme, _, supplied = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not supplied:
        raise _unauthorised()
    if not hmac.compare_digest(supplied.strip().encode(), settings.token.encode()):
        raise _unauthorised()


def _validation_message(exc: RequestValidationError) -> str:
    parts = []
    for error in exc.errors()[:5]:
        location = ".".join(str(p) for p in error.get("loc", ()) if p != "body")
        message = str(error.get("msg", "is invalid")).removeprefix("Value error, ")
        parts.append(f"{location}: {message}" if location else message)
    return "; ".join(parts) or "The request is invalid."


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def _service_error(_: Request, exc: ServiceError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else None
        return JSONResponse(envelope(exc.code, exc.message), status_code=exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
        if any(error.get("type") == "json_invalid" for error in exc.errors()):
            return JSONResponse(envelope("bad_request", "The request body is not valid JSON."), 400)
        return JSONResponse(envelope("invalid_request", _validation_message(exc)), 422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "http_error")
        return JSONResponse(envelope(code, str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Chart calculation failed", exc_info=exc)
        return JSONResponse(envelope("internal_error", "The chart could not be calculated."), 500)


def _install_routes(app: FastAPI) -> None:
    @app.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        return HealthResponse(status="ok", engines=engine_versions())

    @app.post(
        "/v1/chart",
        response_model=ChartPayload,
        response_model_by_alias=True,
        dependencies=[Depends(_check_bearer)],
    )
    def chart(body: ChartRequest, request: Request) -> ChartPayload:
        state = request.app.state
        location = resolve_location(
            body.place,
            body.latitude,
            body.longitude,
            body.timezone,
            state.geocoder,
            state.timezones,
            reject_ambiguous=body.reject_ambiguous_place,
        )
        return build_chart(body, location)


def create_app(
    settings: Settings | None = None,
    geocoder: Geocoder | None = None,
    timezones: TimezoneLookup | None = None,
) -> FastAPI:
    """Build the app. Without `settings`, reads the environment (and may refuse to start)."""
    settings = settings or load_settings()
    if settings.token is None:
        logger.warning("CHART_SERVICE_ALLOW_NO_AUTH=1: authentication is OFF (local development only)")
    resolved_geocoder = geocoder or OfflineGeocoder(settings.geo_min_population)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        warm = getattr(resolved_geocoder, "warm", None)
        if callable(warm):
            warm()
        yield

    app = FastAPI(
        title="Soul Codes chart service", version="1", lifespan=lifespan, docs_url=None, redoc_url=None
    )
    app.state.settings = settings
    app.state.geocoder = resolved_geocoder
    app.state.timezones = timezones or OfflineTimezoneLookup()
    _install_error_handlers(app)
    _install_routes(app)
    return app
