"""System management for UniFi Protect."""


class SystemManager:
    def __init__(self, connection_manager):
        self._cm = connection_manager
