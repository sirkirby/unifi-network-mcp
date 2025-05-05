FROM python:3.13-slim

WORKDIR /app

# Install UV
RUN pip install uv

# Copy pyproject.toml and README.md first to leverage Docker cache
COPY pyproject.toml README.md ./
RUN uv pip install --system .

# Copy the rest of the application
COPY . .

# Expose port for MCP server
EXPOSE 3000

# Command to run the application using the installed entry point
CMD ["mcp-server-unifi-network"]