"""Event management for UniFi Protect."""


class EventManager:
    def __init__(self, connection_manager):
        self._cm = connection_manager
