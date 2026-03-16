.PHONY: help test lint format pre-commit network-test network-lint network-format network-manifest

help:
	@echo "UniFi MCP Ecosystem — Top-Level Commands"
	@echo ""
	@echo "  make test              Run all tests"
	@echo "  make lint              Lint all packages"
	@echo "  make format            Format all packages"
	@echo "  make network-test      Run network server tests"
	@echo "  make network-lint      Lint network server"
	@echo "  make network-manifest  Regenerate network tools manifest"

network-test:
	$(MAKE) -C apps/network test

network-lint:
	$(MAKE) -C apps/network lint

network-format:
	$(MAKE) -C apps/network format

network-manifest:
	$(MAKE) -C apps/network manifest

test: network-test

lint: network-lint

format: network-format

pre-commit: format lint test
