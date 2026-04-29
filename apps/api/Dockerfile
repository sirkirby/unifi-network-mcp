FROM python:3.13-slim

WORKDIR /app

# Version passed from CI/CD (used by hatch-vcs when git is unavailable)
ARG VERSION=0.0.0.dev0
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}

RUN pip install --upgrade pip \
 && pip install uv

# Copy workspace root and member pyproject.toml files (uv needs them to resolve)
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/api/README.md apps/api/README.md
COPY packages/unifi-core/pyproject.toml packages/unifi-core/pyproject.toml
COPY packages/unifi-mcp-shared/pyproject.toml packages/unifi-mcp-shared/pyproject.toml
COPY packages/unifi-mcp-relay/pyproject.toml packages/unifi-mcp-relay/pyproject.toml
COPY apps/network/pyproject.toml apps/network/pyproject.toml
COPY apps/protect/pyproject.toml apps/protect/pyproject.toml
COPY apps/access/pyproject.toml apps/access/pyproject.toml

# Copy api source and its workspace dependency (unifi-core).
# unifi-core source is REQUIRED — Phase 0 wisdom about transitive workspace deps applies:
# without it, hatch-vcs fails with FileNotFoundError writing _version.py.
COPY apps/api/src apps/api/src
COPY apps/api/alembic.ini apps/api/alembic.ini
COPY apps/api/alembic apps/api/alembic
COPY packages/unifi-core/src packages/unifi-core/src

# Install all packages using uv sync (respects lockfile for reproducible builds)
RUN uv sync --frozen --no-dev --package unifi-api

# Use the venv Python directly
ENV PATH="/app/.venv/bin:$PATH"
ENV UNIFI_API_STATE_DIR=/var/lib/unifi-api

# Non-root user with writable state dir
RUN useradd -m -u 1000 -d /home/unifi-api unifi-api \
 && mkdir -p /var/lib/unifi-api \
 && chown -R unifi-api:unifi-api /var/lib/unifi-api
USER unifi-api

EXPOSE 8080

# Console-script entrypoint
CMD ["unifi-api", "serve"]
