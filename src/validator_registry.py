from typing import Dict, Optional, Any, Tuple
from .validators import ResourceValidator
from .schemas import (
    PORT_FORWARD_SCHEMA,
    TRAFFIC_ROUTE_SCHEMA,
    WLAN_SCHEMA,
    NETWORK_SCHEMA,
    VPN_PROFILE_SCHEMA,
    FIREWALL_POLICY_SCHEMA,
    FIREWALL_POLICY_CREATE_SCHEMA,
    PORT_FORWARD_UPDATE_SCHEMA,
    TRAFFIC_ROUTE_UPDATE_SCHEMA,
    WLAN_UPDATE_SCHEMA,
    NETWORK_UPDATE_SCHEMA,
    FIREWALL_POLICY_UPDATE_SCHEMA,
    FIREWALL_POLICY_SIMPLE_SCHEMA,
    TRAFFIC_ROUTE_SIMPLE_SCHEMA,
    QOS_RULE_SIMPLE_SCHEMA,
    PORT_FORWARD_SIMPLE_SCHEMA
)

class UniFiValidatorRegistry:
    """Registry for UniFi Network resource validators."""
    
    _validators = {
        "port_forward": ResourceValidator(PORT_FORWARD_SCHEMA, "Port Forwarding Rule"),
        "traffic_route": ResourceValidator(TRAFFIC_ROUTE_SCHEMA, "Traffic Route"),
        "wlan": ResourceValidator(WLAN_SCHEMA, "Wireless Network"),
        "network": ResourceValidator(NETWORK_SCHEMA, "Network"),
        "vpn_profile": ResourceValidator(VPN_PROFILE_SCHEMA, "VPN Client Profile"),
        "firewall_policy": ResourceValidator(FIREWALL_POLICY_SCHEMA, "Firewall Policy"),
        "firewall_policy_create": ResourceValidator(FIREWALL_POLICY_CREATE_SCHEMA, "Firewall Policy Create"),
        "port_forward_update": ResourceValidator(PORT_FORWARD_UPDATE_SCHEMA, "Port Forwarding Rule Update"),
        "traffic_route_update": ResourceValidator(TRAFFIC_ROUTE_UPDATE_SCHEMA, "Traffic Route Update"),
        "wlan_update": ResourceValidator(WLAN_UPDATE_SCHEMA, "Wireless Network Update"),
        "network_update": ResourceValidator(NETWORK_UPDATE_SCHEMA, "Network Update"),
        "firewall_policy_update": ResourceValidator(FIREWALL_POLICY_UPDATE_SCHEMA, "Firewall Policy Update"),
        "firewall_policy_simple": ResourceValidator(FIREWALL_POLICY_SIMPLE_SCHEMA, "Simple Firewall Policy"),
        "traffic_route_simple": ResourceValidator(TRAFFIC_ROUTE_SIMPLE_SCHEMA, "Simple Traffic Route"),
        "qos_rule_simple": ResourceValidator(QOS_RULE_SIMPLE_SCHEMA, "Simple QoS Rule"),
        "port_forward_simple": ResourceValidator(PORT_FORWARD_SIMPLE_SCHEMA, "Simple Port Forward Rule")
    }
    
    @classmethod
    def get_validator(cls, resource_type: str) -> Optional[ResourceValidator]:
        """Get validator for a resource type."""
        return cls._validators.get(resource_type)
    
    @classmethod
    def validate(cls, resource_type: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
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