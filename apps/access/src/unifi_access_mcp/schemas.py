"""JSON Schema definitions for UniFi Access resources.

Schemas will be added as Access tools are implemented.
"""

from typing import Any, Dict


class AccessResourceRegistry:
    """Registry for UniFi Access resource schemas and validators."""

    _schemas: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_schema(cls, resource_type: str) -> Dict[str, Any]:
        """Get JSON schema for a resource type."""
        return cls._schemas.get(resource_type, {})
