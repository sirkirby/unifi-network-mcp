# Contributing to UniFi Network MCP

## Quick Start

```bash
# Install dependencies
make install

# Check everything works
make info

# Run server locally
make run

# Run tests
make test
```

## Development Workflow

### Adding New Tools

1. **Create tool function** in appropriate module (`src/tools/*.py`)
2. **Add to TOOL_MODULE_MAP** in `src/utils/lazy_tool_loader.py`
3. **Regenerate manifest:**
   ```bash
   make manifest
   ```
4. **Test:**
   ```bash
   make test
   make run-lazy  # Test lazy loading
   ```
5. **Commit both code and manifest:**
   ```bash
   git add src/tools/your_tool.py
   git add src/utils/lazy_tool_loader.py
   git add src/tools_manifest.json
   git commit -m "Add new tool: your_tool"
   ```

### Tool Registration Modes

Test your changes in all three modes:

```bash
# Lazy mode (default, 96% token savings)
make run-lazy

# Eager mode (all tools loaded)
make run-eager

# Meta-only mode (manual discovery)
make run-meta
```

### Code Quality

Before committing:

```bash
# Format code
make format

# Run linters
make lint

# Run tests
make test

# Or all at once:
make pre-commit
```

## Tool Manifest

The `src/tools_manifest.json` file is auto-generated and **must be committed to git**.

### When to Regenerate

Run `make manifest` after:
- Adding new tools
- Removing tools
- Renaming tools
- Changing tool names in `TOOL_MODULE_MAP`

### Why It's Committed

The manifest allows lazy loading mode to discover all tools without importing them.
It's pre-generated so users don't need build tools.

## Testing

### Run All Tests
```bash
make test
```

### Run Specific Tests
```bash
# Batch/async operations
make test-async

# With coverage
make test-cov
```

### Manual Testing

```bash
# Development console (eager mode, all tools available)
make console

# Test with Claude Desktop
# 1. Update your claude_desktop_config.json
# 2. Set command to use local development:
#    "command": "/Users/you/.local/bin/uv"
#    "args": ["--directory", "/path/to/unifi-network-mcp", "run", "python", "-m", "src.main"]
# 3. Restart Claude Desktop
```

## Contributor Workflow

Contributors should **fork** the repository and submit changes via Pull Request:

```bash
# 1. Fork the repo on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/unifi-network-mcp.git
cd unifi-network-mcp

# 3. Create a feature branch
git checkout -b feature/my-new-feature

# 4. Make your changes, then commit
git add .
git commit -m "feat: add my new feature"

# 5. Push to your fork
git push origin feature/my-new-feature

# 6. Open a Pull Request on GitHub
```

**Do not push directly to `main`** - all changes go through PR review.

---

## Release Process (Maintainers Only)

This section is for project maintainers who have push access to the main repository.

### Pre-Release Checklist

```bash
# Run full validation
make pre-release
```

This will:
1. Clean build artifacts
2. Regenerate manifest
3. Format code
4. Run linters
5. Run tests
6. Build packages

### Create Release

**Important:** The version in `pyproject.toml` must match the release tag.

```bash
# 1. Update version in pyproject.toml
#    Edit: version = "0.X.Y"

# 2. Update version in .well-known/mcp-server.json
#    Edit: "version": "0.X.Y"

# 3. Commit changes
git add pyproject.toml .well-known/mcp-server.json
git commit -m "chore: bump version to 0.X.Y"

# 4. Tag release (must match pyproject.toml version)
git tag v0.X.Y

# 5. Push
git push origin main --tags
```

GitHub Actions will automatically:
- Build and publish to PyPI (on release)
- Build and publish Docker images (on tag push)

## Project Structure

```
unifi-network-mcp/
├── src/
│   ├── main.py              # MCP server entry point
│   ├── bootstrap.py         # Configuration
│   ├── tool_index.py        # Tool registry
│   ├── tools_manifest.json  # Pre-generated tool list (commit this!)
│   ├── tools/               # Tool implementations
│   ├── utils/
│   │   ├── lazy_tool_loader.py  # Lazy loading logic + TOOL_MODULE_MAP
│   │   └── meta_tools.py        # Meta-tools: tool_index, execute, batch, batch_status
│   └── config/
│       └── config.yaml      # Server configuration
│
├── scripts/
│   └── generate_tool_manifest.py  # Manifest generator
│
├── tests/
│   └── test_*.py            # Test files
│
├── docs/                    # Documentation
├── examples/                # Usage examples
└── Makefile                 # Development commands
```

## Common Tasks

### Adding a Tool Module

1. Create `src/tools/mynewmodule.py`
2. Add tool names to `TOOL_MODULE_MAP` in `lazy_tool_loader.py`
3. Run `make manifest`
4. Test with `make run-lazy`
5. Update documentation:
   - Add category to `src/config/config.yaml` (enabled_categories comment)
   - Add category to README.md (Tool Categories table)

### Updating Dependencies

```bash
# Add dependency
uv add package-name

# Remove dependency
uv remove package-name

# Update all
uv sync
```

### Debugging

```bash
# Enable debug logging
export UNIFI_LOG_LEVEL=DEBUG
make run

# Use development console for interactive testing
make console
```

## Getting Help

- **Issues:** https://github.com/sirkirby/unifi-network-mcp/issues
- **Discussions:** https://github.com/sirkirby/unifi-network-mcp/discussions
- **Documentation:** See `docs/` directory

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to public functions
- Run `make format` before committing

## Questions?

Check the documentation in `docs/` or open a discussion on GitHub!
