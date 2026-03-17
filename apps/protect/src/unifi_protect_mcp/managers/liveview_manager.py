"""Liveview management for UniFi Protect."""


class LiveviewManager:
    def __init__(self, connection_manager):
        self._cm = connection_manager
