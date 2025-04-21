from __future__ import annotations

"""Bootstrap utilities for the UniFi‑Network MCP server.

This module consolidates:
• environment loading
• logging configuration
• configuration loading / validation

Importing it early guarantees deterministic side‑effects (env + logging) and
exposes a `load_config()` helper that the rest of the codebase can share.
"""

from dataclasses import dataclass
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from omegaconf import OmegaConf

# ---------------------------------------------------------------------------
# Environment & logging
# ---------------------------------------------------------------------------

load_dotenv()


LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LOG_LEVEL = os.getenv("UNIFI_MCP_LOG_LEVEL", "INFO").upper()


def setup_logging(level: str | None = None) -> logging.Logger:
    """Configure root logger once and return the project logger."""
    chosen_level = getattr(logging, (level or DEFAULT_LOG_LEVEL), logging.INFO)

    root_logger = logging.getLogger()
    # Skip re‑adding handlers when running reload in dev
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(handler)
    root_logger.setLevel(chosen_level)

    return logging.getLogger("unifi-network-mcp")


logger = setup_logging()


# ---------------------------------------------------------------------------
# Domain config dataclasses  -------------------------------------------------
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class UniFiSettings:
    host: str
    username: str
    password: str
    port: int = 443
    site: str = "default"
    verify_ssl: bool = False

    @classmethod
    def from_omegaconf(cls, cfg: Any) -> "UniFiSettings":
        """Create from an OmegaConf config object."""
        return cls(
            host=str(cfg.host),
            username=str(cfg.username),
            password=str(cfg.password),
            port=int(cfg.get("port", 443)),
            site=str(cfg.get("site", "default")),
            verify_ssl=bool(cfg.get("verify_ssl", False)),
        )


# ---------------------------------------------------------------------------
# Config loading  -----------------------------------------------------------
# ---------------------------------------------------------------------------

CONFIG_PATH = os.getenv("CONFIG_PATH", "config/config.yaml")


def load_config(path: str | Path = CONFIG_PATH) -> OmegaConf:
    """Load YAML config with environment variable substitution."""
    path = Path(path).expanduser()
    
    if not path.exists():
        logger.error("Configuration file not found: %s", path)
        raise SystemExit(2)

    cfg = OmegaConf.load(str(path))

    # Merge env vars for UniFi settings so they override YAML
    unifi_env_overrides: dict[str, Any] = {}
    for key in ("host", "username", "password", "port", "site", "verify_ssl"):
        env_key = f"UNIFI_{key.upper()}"
        if (val := os.getenv(env_key)) is not None:
            if key == "verify_ssl":
                val = val.lower() in {"1", "true", "yes"}
            unifi_env_overrides[key] = val
    if unifi_env_overrides:
        logger.debug("Applying env overrides to Unifi config: %s", unifi_env_overrides)
        cfg.unifi = OmegaConf.merge(cfg.unifi, unifi_env_overrides)

    return cfg 