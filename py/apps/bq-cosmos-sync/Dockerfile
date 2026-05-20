# syntax=docker/dockerfile:1.7

# ---- builder ----------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /workspace

# Workspace root + sibling lib + the app itself. uv resolves the workspace
# from the root pyproject.toml.
COPY py/pyproject.toml py/pyproject.toml
COPY py/libs/bigquerykit py/libs/bigquerykit
COPY py/libs/cosmosdbkit py/libs/cosmosdbkit
COPY py/apps/bq-cosmos-sync py/apps/bq-cosmos-sync

WORKDIR /workspace/py/apps/bq-cosmos-sync
RUN uv sync --frozen --no-dev || uv sync --no-dev

# ---- runtime ----------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/workspace/py/apps/bq-cosmos-sync/.venv/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 sync \
    && useradd  --uid 1000 --gid 1000 --create-home --shell /sbin/nologin sync

WORKDIR /workspace
COPY --from=builder --chown=sync:sync /workspace /workspace

USER sync

ENTRYPOINT ["python", "-m", "bq_cosmos_sync"]
CMD ["run"]
