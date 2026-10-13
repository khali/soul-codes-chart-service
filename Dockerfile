# Soul Codes chart service. Build from this directory:
#   docker build -t soulcodes-chart-service services/chart-service
# Run (the token is required; the service refuses to start without it):
#   docker run --rm -p 8080:8080 -e CHART_SERVICE_TOKEN="$(openssl rand -hex 32)" soulcodes-chart-service

FROM ghcr.io/astral-sh/uv:0.11.32 AS uv

FROM python:3.11-slim-bookworm AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /src
# Dependencies first, so code changes do not reinstall them.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.11-slim-bookworm
RUN groupadd --system --gid 10001 chart \
    && useradd --system --uid 10001 --gid chart --no-create-home --shell /usr/sbin/nologin chart
COPY --from=build /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER chart
WORKDIR /tmp
EXPOSE 8080

# The geocoder index loads at startup (a few seconds), hence the start period.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4).status != 200)"]

# One worker per container: calculations are serialised by a process-wide lock around
# the Swiss Ephemeris, and each worker holds its own geocoder index (about 115 MB).
CMD ["uvicorn", "soulcodes_chart_service.app:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-server-header"]
