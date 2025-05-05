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
import importlib.resources

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

def load_config(path_override: str | Path | None = None) -> OmegaConf:
    """Load YAML config with environment variable substitution.

    Order of precedence:
    1. Environment variable `CONFIG_PATH`
    2. Path provided via `path_override` argument
    3. Relative path `config/config.yaml` in current working directory
    4. Default `config.yaml` bundled within the package (`src/config/`)
    """
    config_path_str: str | None = os.getenv("CONFIG_PATH")
    if path_override:
        config_path_str = str(path_override)

    resolved_path: Path | None = None

    if config_path_str:
        # 1. Check env var / explicit override
        path = Path(config_path_str).expanduser()
        if path.exists() and path.is_file():
            resolved_path = path
            logger.info("Using configuration file from CONFIG_PATH/override: %s", path)
        else:
            logger.error("Configuration file specified by CONFIG_PATH/override not found: %s", path)
            raise SystemExit(2)  # Exit if specified path is invalid
    else:
        # 2. Check relative path in CWD
        relative_path = Path("config/config.yaml")
        if relative_path.exists() and relative_path.is_file():
            resolved_path = relative_path
            logger.info("Using configuration file from relative path: %s", relative_path)
        else:
            # 3. Use bundled default config
            try:
                # Use importlib.resources to safely access package data
                config_file_ref = importlib.resources.files('src.config').joinpath('config.yaml')
                if config_file_ref.is_file():
                    resolved_path = Path(str(config_file_ref))  # Convert Traversable to Path
                    logger.info("Using bundled default configuration: %s", resolved_path)
                else:
                    logger.error("Bundled default configuration file could not be accessed (not a file).")
                    raise SystemExit(3)  # Exit if bundled config isn't a file
            except (ModuleNotFoundError, FileNotFoundError, Exception) as e:
                logger.error("Could not find or access bundled default configuration: %s", e)
                raise SystemExit(3)  # Exit if bundled config cannot be loaded

    if resolved_path is None:
        # Should not be reachable if logic above is correct, but safeguard
        logger.critical("Failed to determine configuration file path.")
        raise SystemExit(4)

    cfg = OmegaConf.load(str(resolved_path))

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