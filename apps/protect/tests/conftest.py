"""Pytest configuration for unifi-protect-mcp tests."""

import sys
from pathlib import Path

# Add the protect app's src directory to path so unifi_protect_mcp is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
