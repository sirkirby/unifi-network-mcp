.PHONY: help test lint format pre-commit core-test shared-test network-test network-lint network-format network-manifest

help:
	@echo "UniFi MCP Ecosystem — Top-Level Commands"
	@echo ""
	@echo "  make test              Run all tests"
	@echo "  make lint              Lint all packages"
	@echo "  make format            Format all packages"
	@echo "  make core-test         Run core package tests"
	@echo "  make shared-test       Run shared package tests"
	@echo "  make network-test      Run network server tests"
	@echo "  make network-lint      Lint network server"
	@echo "  make network-manifest  Regenerate network tools manifest"

core-test:
	uv run --package unifi-core pytest packages/unifi-core/tests -v

shared-test:
	uv run --package unifi-mcp-shared pytest packages/unifi-mcp-shared/tests -v

network-test:
	$(MAKE) -C apps/network test

network-lint:
	$(MAKE) -C apps/network lint

network-format:
	$(MAKE) -C apps/network format

network-manifest:
	$(MAKE) -C apps/network manifest

test: core-test shared-test network-test

lint: network-lint

format: network-format

pre-commit: format lint test
