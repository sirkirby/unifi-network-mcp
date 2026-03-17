"""Sensor management for UniFi Protect."""


class SensorManager:
    def __init__(self, connection_manager):
        self._cm = connection_manager
