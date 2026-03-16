FROM python:3.13-slim

WORKDIR /app

# Version passed from CI/CD (used by hatch-vcs when git is unavailable)
ARG VERSION=0.0.0.dev0
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}

RUN pip install --upgrade pip \
 && pip install uv

# --- Layer-cached dependency install ---
# Copy workspace root pyproject.toml and lockfile first (changes rarely)
COPY pyproject.toml uv.lock ./

# Copy package metadata for dependency resolution (source changes more often)
COPY apps/network/pyproject.toml apps/network/pyproject.toml
COPY packages/unifi-core/pyproject.toml packages/unifi-core/pyproject.toml
COPY packages/unifi-mcp-shared/pyproject.toml packages/unifi-mcp-shared/pyproject.toml

# Copy README (referenced by apps/network/pyproject.toml)
COPY README.md ./

# Copy package source trees
COPY apps/network/src apps/network/src
COPY packages/unifi-core/src packages/unifi-core/src
COPY packages/unifi-mcp-shared/src packages/unifi-mcp-shared/src

# Install the network app (resolves workspace deps automatically)
RUN uv pip install --system ./apps/network

# Expose the MCP server port (for optional HTTP transport: streamable-http or SSE)
EXPOSE 3000

# Console-script entrypoint
CMD ["unifi-network-mcp"]
