"""Recording management for UniFi Protect."""


class RecordingManager:
    def __init__(self, connection_manager):
        self._cm = connection_manager
