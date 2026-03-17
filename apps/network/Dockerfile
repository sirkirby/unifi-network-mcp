FROM python:3.13-slim

WORKDIR /app

# Version passed from CI/CD (used by hatch-vcs when git is unavailable)
ARG VERSION=0.0.0.dev0

RUN pip install --upgrade pip \
 && pip install uv

# Copy workspace root pyproject.toml and lockfile
COPY pyproject.toml uv.lock ./

# Copy package metadata for dependency resolution
COPY apps/network/pyproject.toml apps/network/pyproject.toml
COPY apps/network/README.md apps/network/README.md
COPY packages/unifi-core/pyproject.toml packages/unifi-core/pyproject.toml
COPY packages/unifi-mcp-shared/pyproject.toml packages/unifi-mcp-shared/pyproject.toml

# Copy package source trees
COPY apps/network/src apps/network/src
COPY packages/unifi-core/src packages/unifi-core/src
COPY packages/unifi-mcp-shared/src packages/unifi-mcp-shared/src

# Install all packages
# SETUPTOOLS_SCM_PRETEND_VERSION makes hatch-vcs use the provided version
# instead of trying to read git tags (which aren't available in Docker)
RUN SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION} \
    uv pip install --system \
    ./packages/unifi-core \
    ./packages/unifi-mcp-shared \
    ./apps/network

# Expose the MCP server port (for optional HTTP transport: streamable-http or SSE)
EXPOSE 3000

# Console-script entrypoint
CMD ["unifi-network-mcp"]
