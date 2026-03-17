"""Validator registry for UniFi Protect resources.

Validators will be registered as Protect tools are implemented.
"""

from typing import Any, Dict, Optional, Tuple

from .validators import ResourceValidator


class ProtectValidatorRegistry:
    """Registry for UniFi Protect resource validators."""

    _validators: Dict[str, ResourceValidator] = {}

    @classmethod
    def get_validator(cls, resource_type: str) -> Optional[ResourceValidator]:
        """Get validator for a resource type."""
        return cls._validators.get(resource_type)

    @classmethod
    def validate(
        cls, resource_type: str, params: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validate parameters for a resource type.

        Args:
            resource_type: The type of resource to validate
            params: The parameters to validate

        Returns:
            Tuple of (is_valid, error_message, validated_params)
        """
        validator = cls.get_validator(resource_type)
        if validator:
            return validator.validate(params)
        return False, f"No validator found for resource type: {resource_type}", None
