"""Configuration parsing utilities.

This module provides helpers for parsing configuration values that may come
from OmegaConf-resolved environment variables (which can be strings like
"true"/"false") or direct boolean values.
"""

from typing import Any


def parse_config_bool(value: Any, default: bool = False) -> bool:
    """Parse a config value as boolean, handling string values from env vars.

    OmegaConf resolves ${oc.env:VAR,default} to strings when the env var is set,
    so "true"/"false" strings need to be parsed explicitly.

    Args:
        value: The config value to parse (string, bool, or None)
        default: Default value if value is None

    Returns:
        Boolean interpretation of the value

    Examples:
        >>> parse_config_bool("true")
        True
        >>> parse_config_bool("false")
        False
        >>> parse_config_bool(True)
        True
        >>> parse_config_bool(None, default=True)
        True
    """
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
