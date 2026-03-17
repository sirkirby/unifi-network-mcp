.PHONY: help test lint format manifest pre-commit core-test shared-test

help:
	@echo "UniFi MCP Ecosystem — Top-Level Commands"
	@echo ""
	@echo "  make test         Run all tests (core + shared + all apps)"
	@echo "  make lint         Lint all apps"
	@echo "  make format       Format all apps"
	@echo "  make manifest     Regenerate tool manifests for all apps"
	@echo "  make pre-commit   Format + lint + test"
	@echo ""
	@echo "  make core-test    Run unifi-core tests only"
	@echo "  make shared-test  Run unifi-mcp-shared tests only"

core-test:
	uv run --package unifi-core pytest packages/unifi-core/tests -v

shared-test:
	uv run --package unifi-mcp-shared pytest packages/unifi-mcp-shared/tests -v

test: core-test shared-test
	$(MAKE) -C apps/network test
	$(MAKE) -C apps/protect test

lint:
	$(MAKE) -C apps/network lint
	$(MAKE) -C apps/protect lint

format:
	$(MAKE) -C apps/network format
	$(MAKE) -C apps/protect format

manifest:
	$(MAKE) -C apps/network manifest
	$(MAKE) -C apps/protect manifest

pre-commit: format lint test
