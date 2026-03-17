"""Shared configuration helpers: logging setup and YAML config loading.

These are the generic parts extracted from the network app's bootstrap.py.
App-specific settings (UniFiSettings, load_dotenv, env var merging) remain
in each app's own bootstrap module.
"""

import logging
import sys
from pathlib import Path

from omegaconf import OmegaConf

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging(logger_name: str, level: str | None = None) -> logging.Logger:
    """Configure the root logger once and return a named logger.

    Adds a stderr handler with a standard format if one is not already present.
    This is idempotent -- calling it multiple times will not duplicate handlers.

    Args:
        logger_name: The name passed to ``logging.getLogger`` (e.g.
                     ``"unifi-network-mcp"``).
        level: Optional log level string (``"DEBUG"``, ``"INFO"``, etc.).
               Falls back to ``"INFO"`` if not provided.

    Returns:
        A :class:`logging.Logger` with the given *logger_name*.
    """
    chosen_level = getattr(logging, (level or "INFO").upper(), logging.INFO)

    root_logger = logging.getLogger()
    # Skip re-adding handlers when running reload in dev
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(handler)
    root_logger.setLevel(chosen_level)

    return logging.getLogger(logger_name)


def load_yaml_config(path: str | Path) -> OmegaConf:
    """Load a YAML configuration file via OmegaConf.

    OmegaConf resolves ``${oc.env:VAR,default}`` interpolations at access time,
    so environment variables are respected without any extra merging step.

    Args:
        path: Filesystem path to the YAML file.

    Returns:
        An OmegaConf ``DictConfig`` object.

    Raises:
        FileNotFoundError: If *path* does not exist.
    """
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Configuration file not found: {resolved}")

    return OmegaConf.load(str(resolved))
