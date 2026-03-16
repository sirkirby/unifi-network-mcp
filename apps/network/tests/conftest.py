"""Pytest configuration for unifi-network-mcp tests."""

import sys
from pathlib import Path

# Add the network app's src directory to path so unifi_network_mcp is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
