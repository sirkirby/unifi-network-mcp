"""Per-controller subscriber pool for SSE streaming.

The pool owns at most one manager-callback registration per
(controller_id, product) key. Multiple HTTP clients connecting to the same
stream get separate StreamSubscribers, each with a bounded asyncio.Queue;
the pool's broadcast helper fans out incoming events to all of them.
"""

from __future__ import annotations

import asyncio
import logging
import weakref
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("unifi-api.streams")


@dataclass
class StreamSubscriber:
    queue: asyncio.Queue[dict | None] = field(default_factory=lambda: asyncio.Queue(maxsize=256))
    filter_fn: Callable[[dict], bool] | None = None


class SubscriberPool:
    """Per (controller_id, product) registry of HTTP-client subscribers."""

    def __init__(self, queue_maxsize: int = 256) -> None:
        self._pools: dict[tuple[str, str], list[StreamSubscriber]] = {}
        self._unsubs: dict[tuple[str, str], Callable[[], None]] = {}
        self._managers: dict[tuple[str, str], Any] = {}
        self._discarded: weakref.WeakSet[Any] = weakref.WeakSet()
        self._queue_maxsize = queue_maxsize

    async def attach(self, controller_id: str, product: str, manager: Any) -> StreamSubscriber:
        key = (controller_id, product)
        sub = StreamSubscriber(queue=asyncio.Queue(maxsize=self._queue_maxsize))
        if manager in self._discarded:
            sub.queue.put_nowait(None)
            return sub
        previous = self._managers.get(key)
        if previous is not None and previous is not manager:
            self.disconnect_manager(previous)
        self._pools.setdefault(key, []).append(sub)
        if key not in self._unsubs:
            self._unsubs[key] = manager.add_subscriber(
                lambda evt, k=key, m=manager: self._broadcast(k, evt) if self._managers.get(k) is m else None
            )
            self._managers[key] = manager
            logger.debug("[streams] attached manager callback for %s", key)
        return sub

    def disconnect_manager(self, manager: Any) -> None:
        """End streams tied to a discarded manager so clients can reconnect."""
        self._discarded.add(manager)
        for key in [key for key, value in self._managers.items() if value is manager]:
            self._managers.pop(key)
            unsub = self._unsubs.pop(key, None)
            if unsub is not None:
                try:
                    unsub()
                except Exception as exc:
                    logger.debug("[streams] unsubscribe failed: %s", type(exc).__name__)
            for sub in self._pools.pop(key, []):
                # Discard buffered data from the old credential generation and
                # make room for the termination signal even for a slow client.
                while not sub.queue.empty():
                    sub.queue.get_nowait()
                sub.queue.put_nowait(None)

    async def detach(self, controller_id: str, product: str, sub: StreamSubscriber) -> None:
        key = (controller_id, product)
        try:
            self._pools.get(key, []).remove(sub)
        except ValueError:
            return
        if not self._pools.get(key):
            unsub = self._unsubs.pop(key, None)
            if unsub is not None:
                try:
                    unsub()
                except Exception:
                    logger.debug("[streams] error unsubscribing %s", key)
            self._pools.pop(key, None)
            self._managers.pop(key, None)
            logger.debug("[streams] detached last subscriber for %s", key)

    def _broadcast(self, key: tuple[str, str], event: dict) -> None:
        for sub in list(self._pools.get(key, [])):
            if sub.filter_fn is not None and not sub.filter_fn(event):
                continue
            try:
                sub.queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("[streams] queue full for subscriber on %s; dropping event", key)
