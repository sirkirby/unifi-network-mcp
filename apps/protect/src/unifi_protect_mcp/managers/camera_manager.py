"""Camera management for UniFi Protect."""


class CameraManager:
    def __init__(self, connection_manager):
        self._cm = connection_manager
