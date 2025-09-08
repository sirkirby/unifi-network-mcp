from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Iterable

_logger = logging.getLogger("unifi-network-mcp.diagnostics")


def _get_bool_env(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    val = os.getenv(name)
    if not val:
        return default
    try:
        return int(val)
    except Exception:
        return default


def _server_diag_cfg_from_env() -> Dict[str, Any]:
    return {
        "enabled": _get_bool_env("UNIFI_MCP_DIAGNOSTICS", False),
        "log_tool_args": _get_bool_env("UNIFI_MCP_DIAG_LOG_TOOL_ARGS", True),
        "log_tool_result": _get_bool_env("UNIFI_MCP_DIAG_LOG_TOOL_RESULT", True),
        "max_payload_chars": _get_int_env("UNIFI_MCP_DIAG_MAX_PAYLOAD", 2000),
    }


def _server_diag_cfg_from_config() -> Dict[str, Any]:
    try:
        # Import lazily to avoid circular imports at module load time
        from src.runtime import config  # noqa: WPS433

        server_cfg = getattr(config, "server", {}) or {}
        diag_cfg = server_cfg.get("diagnostics", {}) or {}
        # Fallbacks will be applied in accessors below
        return {
            "enabled": bool(diag_cfg.get("enabled", False)),
            "log_tool_args": bool(diag_cfg.get("log_tool_args", True)),
            "log_tool_result": bool(diag_cfg.get("log_tool_result", True)),
            "max_payload_chars": int(diag_cfg.get("max_payload_chars", 2000)),
        }
    except Exception:
        return _server_diag_cfg_from_env()


def _diag_cfg() -> Dict[str, Any]:
    # Config takes precedence, env is fallback
    cfg = _server_diag_cfg_from_config()
    return cfg


def diagnostics_enabled() -> bool:
    return bool(_diag_cfg().get("enabled", False))


_REDACT_KEYS = {
    "password",
    "x_password",
    "x_passphrase",
    "passphrase",
    "token",
    "authorization",
    "auth",
    "cookie",
}


def _redact_value(key: str, value: Any) -> Any:
    if key.lower() in _REDACT_KEYS:
        return "***REDACTED***"
    return value


def _redact(obj: Any) -> Any:
    try:
        if isinstance(obj, dict):
            return {k: _redact(v) if k.lower() not in _REDACT_KEYS else "***REDACTED***" for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [ _redact(v) for v in obj ]
        return obj
    except Exception:
        return obj


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [truncated {len(text) - limit} chars]"


def _safe_json(data: Any, limit: int) -> str:
    try:
        redacted = _redact(data)
        as_text = json.dumps(redacted, ensure_ascii=False, default=str)
    except Exception:
        try:
            as_text = str(data)
        except Exception:
            as_text = "<unserializable>"
    return _truncate(as_text, limit)


def log_tool_call(tool_name: str, args: Any, kwargs: Dict[str, Any], result: Any | None, duration_ms: float, error: Exception | None = None) -> None:
    if not diagnostics_enabled():
        return
    cfg = _diag_cfg()
    parts = {"tool": tool_name, "duration_ms": int(duration_ms)}
    if cfg.get("log_tool_args", True):
        try:
            parts["args"] = args
            parts["kwargs"] = kwargs
        except Exception:
            parts["args"] = "<unserializable>"
            parts["kwargs"] = "<unserializable>"
    if error is not None:
        parts["error"] = str(error)
    elif cfg.get("log_tool_result", True):
        parts["result"] = result

    # Serialize with redaction + truncation
    max_chars = int(cfg.get("max_payload_chars", 2000))
    text = _safe_json(parts, max_chars)
    _logger.info("TOOL %s", text)


def wrap_tool(func, tool_name: str):
    async def _wrapper(*args, **kwargs):
        if not diagnostics_enabled():
            return await func(*args, **kwargs)
        start = time.perf_counter()
        err: Exception | None = None
        res: Any | None = None
        try:
            res = await func(*args, **kwargs)
            return res
        except Exception as e:  # noqa: BLE001 - we re-raise after logging
            err = e
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            try:
                log_tool_call(tool_name, args, kwargs, res, duration_ms, err)
            except Exception:
                # Never let diagnostics break the tool
                pass
    return _wrapper


def log_api_request(method: str, path: str, payload: Any, response: Any, duration_ms: float, ok: bool) -> None:
    if not diagnostics_enabled():
        return
    cfg = _diag_cfg()
    max_chars = int(cfg.get("max_payload_chars", 2000))
    entry = {
        "method": method.upper(),
        "path": path,
        "ok": ok,
        "duration_ms": int(duration_ms),
        "request": json.loads(_safe_json(payload, max_chars)) if payload is not None else None,
        "response": json.loads(_safe_json(response, max_chars)) if response is not None else None,
    }
    _logger.info("API %s", _safe_json(entry, max_chars))


