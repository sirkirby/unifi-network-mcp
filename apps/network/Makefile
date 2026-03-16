.PHONY: help test test-cov lint format format-check manifest run run-lazy run-eager run-meta pre-commit clean

help:
	@echo "UniFi Network MCP — Development Commands"
	@echo ""
	@echo "  make test       Run tests"
	@echo "  make lint       Lint with ruff"
	@echo "  make format     Format with ruff"
	@echo "  make manifest   Regenerate tools_manifest.json"
	@echo "  make run        Run server (default: lazy mode)"
	@echo "  make clean      Remove build artifacts"

test:
	cd ../.. && uv run --package unifi-network-mcp pytest apps/network/tests -v

test-cov:
	cd ../.. && uv run --package unifi-network-mcp pytest apps/network/tests -v --cov=unifi_network_mcp --cov-report=term-missing

lint:
	cd ../.. && uv run ruff check apps/network/src apps/network/tests

format:
	cd ../.. && uv run ruff format apps/network/src apps/network/tests

format-check:
	cd ../.. && uv run ruff format --check apps/network/src apps/network/tests

manifest:
	cd ../.. && uv run --package unifi-network-mcp python apps/network/scripts/generate_tool_manifest.py

run:
	cd ../.. && UNIFI_TOOL_REGISTRATION_MODE=lazy uv run --package unifi-network-mcp unifi-network-mcp

run-lazy:
	cd ../.. && UNIFI_TOOL_REGISTRATION_MODE=lazy uv run --package unifi-network-mcp unifi-network-mcp

run-eager:
	cd ../.. && UNIFI_TOOL_REGISTRATION_MODE=eager uv run --package unifi-network-mcp unifi-network-mcp

run-meta:
	cd ../.. && UNIFI_TOOL_REGISTRATION_MODE=meta_only uv run --package unifi-network-mcp unifi-network-mcp

pre-commit: format lint test

clean:
	rm -rf build/ dist/ *.egg-info src/unifi_network_mcp/_version.py
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
