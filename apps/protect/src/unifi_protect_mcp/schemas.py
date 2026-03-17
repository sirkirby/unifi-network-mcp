"""JSON Schema definitions for UniFi Protect resources.

Schemas will be added as Protect tools are implemented.
"""

from typing import Any, Dict


class ProtectResourceRegistry:
    """Registry for UniFi Protect resource schemas and validators."""

    _schemas: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_schema(cls, resource_type: str) -> Dict[str, Any]:
        """Get JSON schema for a resource type."""
        return cls._schemas.get(resource_type, {})
