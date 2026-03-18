"""Pytest configuration for unifi-access-mcp tests."""

import sys
from pathlib import Path

# Add the access app's src directory to path so unifi_access_mcp is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
