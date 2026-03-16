.PHONY: help test lint format pre-commit network-test network-lint network-format network-manifest shared-test

help:
	@echo "UniFi MCP Ecosystem — Top-Level Commands"
	@echo ""
	@echo "  make test              Run all tests"
	@echo "  make lint              Lint all packages"
	@echo "  make format            Format all packages"
	@echo "  make shared-test       Run shared package tests"
	@echo "  make network-test      Run network server tests"
	@echo "  make network-lint      Lint network server"
	@echo "  make network-manifest  Regenerate network tools manifest"

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

test: shared-test network-test

lint: network-lint

format: network-format

pre-commit: format lint test
