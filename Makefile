.PHONY: help install dev test lint format clean manifest build docker run

# Default target - show help
help:
	@echo "UniFi Network MCP - Development Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install      - Install dependencies with uv"
	@echo "  make dev          - Install dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run           - Run MCP server locally"
	@echo "  make console       - Start interactive dev console (auto-detect)"
	@echo "  make console-debug - Start dev console with debug logging"
	@echo "  make console-proxy - Force UniFi OS mode + debug logging"
	@echo "  make console-direct- Force standalone mode + debug logging"
	@echo "  make manifest      - Regenerate tool manifest (after adding tools)"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo ""
	@echo "Build & Release:"
	@echo "  make build        - Build package (wheel + sdist)"
	@echo "  make docker       - Build Docker image"
	@echo "  make clean        - Clean build artifacts"
	@echo ""
	@echo "Tool Registration Modes:"
	@echo "  make run-lazy     - Run with lazy loading (default)"
	@echo "  make run-eager    - Run with eager loading (all tools)"
	@echo "  make run-meta     - Run with meta-only mode"

# Setup
install:
	@echo "📦 Installing dependencies..."
	uv sync

dev: install
	@echo "🔧 Installing dev dependencies..."
	uv sync --group dev

# Development
run:
	@echo "🚀 Starting MCP server (lazy mode)..."
	uv run python -m src.main

run-lazy:
	@echo "🚀 Starting MCP server (lazy mode - 96% token savings)..."
	UNIFI_TOOL_REGISTRATION_MODE=lazy uv run python -m src.main

run-eager:
	@echo "🚀 Starting MCP server (eager mode - all tools loaded)..."
	UNIFI_TOOL_REGISTRATION_MODE=eager uv run python -m src.main

run-meta:
	@echo "🚀 Starting MCP server (meta-only mode)..."
	UNIFI_TOOL_REGISTRATION_MODE=meta_only uv run python -m src.main

manifest:
	@echo "🔨 Regenerating tool manifest..."
	uv run python scripts/generate_tool_manifest.py
	@echo "✅ Manifest updated at src/tools_manifest.json"
	@echo "💡 Commit this file to git!"

# Testing
test:
	@echo "🧪 Running tests..."
	uv run pytest tests/ -v

test-cov:
	@echo "🧪 Running tests with coverage..."
	uv run pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-async:
	@echo "🧪 Running async job tests..."
	uv run pytest tests/test_async_jobs.py -v

# Code Quality
lint:
	@echo "🔍 Running linters..."
	uv run ruff check src/ tests/

format:
	@echo "✨ Formatting code..."
	uv run ruff format src/ tests/

format-check:
	@echo "🔍 Checking code formatting..."
	uv run ruff format --check src/ tests/

# Build
build: manifest
	@echo "📦 Building package..."
	uv run python -m build
	@echo "✅ Built packages:"
	@ls -lh dist/*.whl dist/*.tar.gz

build-test: manifest
	@echo "🧪 Test build in clean environment..."
	rm -rf /tmp/unifi-build-test
	uv run python -m build --outdir /tmp/unifi-build-test
	@echo "✅ Build test successful!"
	@echo "📦 Test packages at /tmp/unifi-build-test/"

docker:
	@echo "🐳 Building Docker image..."
	docker build -t unifi-network-mcp:latest .
	@echo "✅ Docker image built: unifi-network-mcp:latest"

docker-run:
	@echo "🐳 Running Docker container..."
	docker run --rm \
		-e UNIFI_HOST=${UNIFI_HOST} \
		-e UNIFI_USERNAME=${UNIFI_USERNAME} \
		-e UNIFI_PASSWORD=${UNIFI_PASSWORD} \
		unifi-network-mcp:latest

# Cleanup
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleaned!"

# Dev Console
console:
	@echo "🔧 Starting development console..."
	UNIFI_TOOL_REGISTRATION_MODE=eager uv run python devtools/dev_console.py

console-debug:
	@echo "🔧 Starting development console (debug logging)..."
	UNIFI_MCP_LOG_LEVEL=DEBUG UNIFI_TOOL_REGISTRATION_MODE=eager uv run python devtools/dev_console.py

console-proxy:
	@echo "🔧 Starting development console (UniFi OS / proxy mode + debug)..."
	UNIFI_CONTROLLER_TYPE=proxy UNIFI_MCP_LOG_LEVEL=DEBUG UNIFI_TOOL_REGISTRATION_MODE=eager uv run python devtools/dev_console.py

console-direct:
	@echo "🔧 Starting development console (standalone / direct mode + debug)..."
	UNIFI_CONTROLLER_TYPE=direct UNIFI_MCP_LOG_LEVEL=DEBUG UNIFI_TOOL_REGISTRATION_MODE=eager uv run python devtools/dev_console.py

# Quick checks before commit
pre-commit: format lint test
	@echo "✅ Pre-commit checks passed!"

# Release preparation
pre-release: clean manifest format lint test build
	@echo "✅ Release preparation complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Review changes: git status"
	@echo "  2. Commit manifest: git add src/tools_manifest.json"
	@echo "  3. Create release: git tag v0.2.0"
	@echo "  4. Push: git push origin main --tags"

# Show current configuration
info:
	@echo "📊 Project Information"
	@echo ""
	@echo "Python version:"
	@python --version
	@echo ""
	@echo "UV version:"
	@uv --version
	@echo ""
	@echo "Tool manifest:"
	@if [ -f src/tools_manifest.json ]; then \
		echo "  ✅ Exists ($(shell jq -r '.count' src/tools_manifest.json) tools)"; \
	else \
		echo "  ❌ Missing - run 'make manifest'"; \
	fi
	@echo ""
	@echo "Git status:"
	@git status --short

# Permission testing helpers
run-with-all-permissions:
	@echo "🔓 Running with ALL permissions enabled..."
	@echo "⚠️  WARNING: This enables high-risk operations!"
	UNIFI_PERMISSIONS_NETWORKS_CREATE=true \
	UNIFI_PERMISSIONS_NETWORKS_UPDATE=true \
	UNIFI_PERMISSIONS_WLANS_CREATE=true \
	UNIFI_PERMISSIONS_WLANS_UPDATE=true \
	UNIFI_PERMISSIONS_DEVICES_CREATE=true \
	UNIFI_PERMISSIONS_DEVICES_UPDATE=true \
	UNIFI_PERMISSIONS_CLIENTS_UPDATE=true \
	uv run python -m src.main

run-read-only:
	@echo "🔒 Running in read-only mode (all modify permissions disabled)..."
	@echo "💡 This is safe for testing with production controllers"
	UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE=false \
	UNIFI_PERMISSIONS_FIREWALL_POLICIES_UPDATE=false \
	UNIFI_PERMISSIONS_TRAFFIC_ROUTES_CREATE=false \
	UNIFI_PERMISSIONS_TRAFFIC_ROUTES_UPDATE=false \
	UNIFI_PERMISSIONS_PORT_FORWARDS_CREATE=false \
	UNIFI_PERMISSIONS_PORT_FORWARDS_UPDATE=false \
	UNIFI_PERMISSIONS_QOS_RULES_CREATE=false \
	UNIFI_PERMISSIONS_QOS_RULES_UPDATE=false \
	UNIFI_PERMISSIONS_VPN_CLIENTS_UPDATE=false \
	UNIFI_PERMISSIONS_VPN_SERVERS_UPDATE=false \
	uv run python -m src.main
