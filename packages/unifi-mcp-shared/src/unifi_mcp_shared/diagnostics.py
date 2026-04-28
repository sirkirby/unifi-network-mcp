"""Compatibility shim. Real implementation lives in unifi_core.diagnostics."""
from unifi_core.diagnostics import *  # noqa: F401,F403
from unifi_core.diagnostics import _redact, _safe_json, _truncate  # noqa: F401
