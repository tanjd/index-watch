# -----------------------------------------------------------------------------
# Stage 1: builder — install deps and app with uv; venv stays in /app/.venv
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir uv

COPY --link pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --link src ./src/
COPY --link data ./data/
COPY --link .env.example ./
RUN uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Stage 2: runtime — copy only venv + app; no uv, no build tools
# -----------------------------------------------------------------------------
FROM python:3.13-slim

WORKDIR /app

# Copy venv and app from builder (same base so venv paths are valid)
COPY --from=builder --link /app/.venv /app/.venv
COPY --from=builder --link /app/src /app/src
COPY --from=builder --link /app/data /app/data
COPY --from=builder --link /app/.env.example /app/.env.example

RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1
ENV HEALTH_PORT=9999
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9999/health')" || exit 1

CMD ["python", "-m", "src.index"]
