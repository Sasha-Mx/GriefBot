# =============================================================================
# GriefBot Retirement Service — Multi-stage Docker build
# =============================================================================

# --- Stage 1: Builder ---
FROM ghcr.io/meta-pytorch/openenv-base:latest AS builder

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/env
WORKDIR /app/env

# Install dependencies into a virtualenv
RUN python -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir -r server/requirements.txt && \
    /app/.venv/bin/pip install --no-cache-dir .

# --- Stage 2: Runtime ---
FROM ghcr.io/meta-pytorch/openenv-base:latest AS runtime

# Copy virtual environment and application from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/env /app/env

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/env:$PYTHONPATH"

WORKDIR /app/env

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
