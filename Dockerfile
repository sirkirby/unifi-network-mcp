FROM python:3.14-slim

WORKDIR /app

# Version passed from CI/CD (used by hatch-vcs when git is unavailable)
ARG VERSION=0.0.0.dev0
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}

RUN pip install --upgrade pip \
 && pip install uv

# Copy only metadata to leverage layer caching
COPY pyproject.toml README.md ./

# Bring in package code needed for installation
COPY src ./src

# Build & install package (pulls aiounifi from PyPI per pyproject)
RUN pip install .

# Do NOT copy the entire repository to avoid shadowing installed deps with
# similarly named top-level folders (e.g., aiounifi/). If you need runtime
# config defaults available without a bind mount, copy only config.
COPY src/config ./src/config

# Expose the MCP server port (for optional HTTP SSE mode)
EXPOSE 3000

# Console-script entrypoint
CMD ["unifi-network-mcp"]