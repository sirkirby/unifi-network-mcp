"""Light management for UniFi Protect."""


class LightManager:
    def __init__(self, connection_manager):
        self._cm = connection_manager
