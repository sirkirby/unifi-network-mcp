"""Tail-of-file reader for the rotating JSON application log."""

from __future__ import annotations

import json
from pathlib import Path


class LogReader:
    """Read recent JSON-per-line log entries from a single file (no rotation
    awareness — RotatingFileHandler keeps the active file ≤ maxBytes).
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def size_bytes(self) -> int:
        try:
            return self._path.stat().st_size
        except FileNotFoundError:
            return 0

    def tail(
        self,
        *,
        limit: int = 50,
        level: str | None = None,
        logger: str | None = None,
        q: str | None = None,
    ) -> list[dict]:
        """Return up to ``limit`` recent log entries, most-recent-first.

        Filters:
          * ``level`` — exact match on ``payload["level"]`` (case-insensitive).
          * ``logger`` — exact match on ``payload["logger"]``.
          * ``q`` — case-insensitive substring match against the raw line.

        Malformed (non-JSON) lines are skipped silently.
        Missing file → ``[]``.
        """
        try:
            text = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []

        out: list[dict] = []
        level_norm = level.upper() if level else None

        for line in reversed(text.splitlines()):
            if not line.strip():
                continue
            if q is not None and q.lower() not in line.lower():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if level_norm is not None and str(payload.get("level", "")).upper() != level_norm:
                continue
            if logger is not None and payload.get("logger") != logger:
                continue
            out.append(payload)
            if len(out) >= limit:
                break
        return out
