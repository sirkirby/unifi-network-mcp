"""Pytest configuration for unifi-api tests."""

import sys
from pathlib import Path

# Add the api app's src directory to path so unifi_api is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
