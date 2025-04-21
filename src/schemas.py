from typing import Dict, Any, Optional
import copy

# Port forwarding rule schema
PORT_FORWARD_SCHEMA = {
    "type": "object",
    "required": ["name", "dst_port", "fwd_port", "fwd_ip"],
    "properties": {
        "name": {"type": "string", "description": "Descriptive name for the port forwarding rule"},
        "dst_port": {"type": "string", "description": "Destination port (external port)"},
        "fwd_port": {"type": "string", "description": "Port to forward to (internal port)"},
        "fwd_ip": {"type": "string", "description": "IP address to forward to"},
        "protocol": {
            "type": "string", 
            "enum": ["tcp", "udp", "tcp_udp"], 
            "default": "tcp_udp",
            "description": "Network protocol"
        },
        "enabled": {"type": "boolean", "default": True, "description": "Whether rule is initially enabled"}
    }
}

# Port forwarding rule update schema (all fields optional)
PORT_FORWARD_UPDATE_SCHEMA = copy.deepcopy(PORT_FORWARD_SCHEMA)
PORT_FORWARD_UPDATE_SCHEMA.pop("required", None) # Remove the required field
# Make all properties optional for update
for prop in PORT_FORWARD_UPDATE_SCHEMA.get("properties", {}):
    PORT_FORWARD_UPDATE_SCHEMA["properties"][prop].pop("default", None) # Remove defaults for update

# Traffic route schema - Updated for V2 API structure
TRAFFIC_ROUTE_SCHEMA = {
    "type": "object",
    # Keep name/interface required based on POST API errors
    # Added network_id and target_devices as required based on API validation error for create
    "required": ["name", "interface", "matching_target", "network_id", "target_devices"], 
    "properties": {
        "name": {"type": "string", "description": "Descriptive name for the route"},
        "interface": {"type": "string", "description": "Interface name (e.g., 'wan', 'wan2', 'vpnclient0') required for creation"},
        "description": {"type": "string", "description": "Additional description"},
        "enabled": {"type": "boolean", "default": True, "description": "Whether route is enabled initially"},
        "matching_target": {
            "type": "string",
            "description": "Specifies the destination/source type",
            "enum": ["INTERNET", "DOMAIN", "IP", "REGION"] 
        },
        # network_id is now required for creation according to API errors
        "network_id": {"type": "string", "description": "Network ID (LAN/VLAN) the route applies to (Required for creation)"},
        # target_devices is now required for creation according to API errors
        # It specifies WHICH devices/networks on the source network_id are affected
        "target_devices": {
            "type": "array",
            "description": "List of client devices or networks the route applies to (Required, cannot be empty). Defines the source scope within network_id.",
            "minItems": 1, # Explicitly require at least one item based on API error
            "items": {
                "type": "object",
                "required": ["type"], # Type is always needed
                "properties": {
                    # client_mac OR network_id should be present based on type
                    "client_mac": {"type": "string", "format": "mac", "description": "MAC address of the client (Required if type is CLIENT)"},
                    "network_id": {"type": "string", "description": "Network ID if type is NETWORK (Required if type is NETWORK)"},
                    "type": {"type": "string", "enum": ["CLIENT", "NETWORK"], "description": "Type of target: CLIENT or NETWORK"}
                },
                "allOf": [ # Add conditional requirements for client_mac/network_id
                    {
                        "if": {"properties": {"type": {"const": "CLIENT"}}},
                        "then": {"required": ["client_mac"]}
                    },
                    {
                        "if": {"properties": {"type": {"const": "NETWORK"}}},
                        "then": {"required": ["network_id"]}
                    }
                ]
            }
        },
        # Other fields matching TypedTrafficRoute model (made optional here, API validates)
        "domains": {
            "type": "array", 
            "description": "List of domains with ports (used with matching_target: DOMAIN)",
            "items": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "ports": {"type": "array", "items": {"type": "integer"}},
                    "port_ranges": {"type": "array", "items": {"type": "object", "properties": {"port_start": {"type": "integer"}, "port_stop": {"type": "integer"}}}}
                }
            }
        },
        "ip_addresses": {
            "type": "array", 
            "description": "List of IPs/subnets with ports (used with matching_target: IP)",
            "items": {
                 "type": "object",
                 "properties": {
                    "ip_or_subnet": {"type": "string"},
                    "ip_version": {"type": "string"},
                    "ports": {"type": "array", "items": {"type": "integer"}},
                    "port_ranges": {"type": "array", "items": {"type": "object", "properties": {"port_start": {"type": "integer"}, "port_stop": {"type": "integer"}}}}
                 }
            }
        },
        "ip_ranges": {
            "type": "array", 
            "description": "List of IP ranges",
            "items": {
                "type": "object",
                "properties": {
                    "ip_start": {"type": "string"},
                    "ip_stop": {"type": "string"},
                    "ip_version": {"type": "string"}
                }
            }
        },
        "regions": {"type": "array", "items": {"type": "string"}, "description": "List of regions (used with matching_target: REGION)"},
        "kill_switch_enabled": {"type": "boolean", "default": False, "description": "Whether kill switch is enabled (for VPNs)"},
        "next_hop": {"type": "string", "description": "Next hop IP address (advanced routing)"}
    },
}

# Traffic route update schema (derived from above, removes name/interface, makes fields optional)
TRAFFIC_ROUTE_UPDATE_SCHEMA = copy.deepcopy(TRAFFIC_ROUTE_SCHEMA)
# Remove fields not settable via update or missing from GET/PUT model
TRAFFIC_ROUTE_UPDATE_SCHEMA["properties"].pop("interface", None)
TRAFFIC_ROUTE_UPDATE_SCHEMA["properties"].pop("name", None) 
# Updates are partial, so top-level fields aren't required for the UPDATE operation itself
# However, the items within arrays might still have requirements (handled by schema)
TRAFFIC_ROUTE_UPDATE_SCHEMA.pop("required", None)

# Make all remaining top-level properties optional for update
for prop in TRAFFIC_ROUTE_UPDATE_SCHEMA.get("properties", {}):
    TRAFFIC_ROUTE_UPDATE_SCHEMA["properties"][prop].pop("default", None)

# Simplified high-level Traffic Route schema for LLM-friendly creation
TRAFFIC_ROUTE_SIMPLE_SCHEMA = {
    "type": "object",
    "required": [
        "name",
        "interface",
        "network",
        "matching_target",
    ],
    "properties": {
        "name": {"type": "string"},
        "interface": {"type": "string"},
        "network": {"type": "string", "description": "Source LAN/VLAN name or id"},
        "client_macs": {
            "type": "array",
            "items": {"type": "string", "format": "mac"},
            "description": "Optional list of client MACs within the network. If omitted the entire network is routed."
        },
        "matching_target": {"type": "string", "enum": ["INTERNET", "DOMAIN", "IP", "REGION"]},
        "destinations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Destination values depending on matching_target (domain names, IPs, regions). Not required for INTERNET."
        },
        "enabled": {"type": "boolean"}
    }
}

# WLAN (Wireless Network) schema
WLAN_SCHEMA = {
    "type": "object",
    "required": ["name", "security", "enabled"],
    "properties": {
        "name": {"type": "string", "description": "Name of the wireless network (SSID)"},
        "security": {
            "type": "string",
            "enum": ["open", "wpa-psk", "wpa2-psk", "wpa3", "wpapsk", "wep"],
            "description": "Security protocol"
        },
        "x_passphrase": {"type": "string", "description": "Password for the wireless network"},
        "enabled": {"type": "boolean", "description": "Whether the network is enabled"},
        "hide_ssid": {"type": "boolean", "default": False, "description": "Whether to hide the SSID"},
        "guest_policy": {"type": "boolean", "default": False, "description": "Whether this is a guest network"},
        "usergroup_id": {"type": "string", "description": "User group ID"},
        "networkconf_id": {"type": "string", "description": "Network configuration ID"}
    },
    "allOf": [
        {
            "if": {
                "properties": {"security": {"enum": ["open"]}}
            },
            "then": {}
        },
        {
            "if": {
                "properties": {"security": {"not": {"enum": ["open"]}}}
            },
            "then": {"required": ["x_passphrase"]}
        }
    ]
}

# WLAN update schema
WLAN_UPDATE_SCHEMA = copy.deepcopy(WLAN_SCHEMA)
WLAN_UPDATE_SCHEMA.pop("required", None)
WLAN_UPDATE_SCHEMA.pop("allOf", None) # Remove conditional requirement for update
# Make all properties optional for update
for prop in WLAN_UPDATE_SCHEMA.get("properties", {}):
    WLAN_UPDATE_SCHEMA["properties"][prop].pop("default", None)

# Network schema (LAN/VLAN)
NETWORK_SCHEMA = {
    "type": "object",
    "required": ["name", "purpose"],
    "properties": {
        "name": {"type": "string", "description": "Network name"},
        "purpose": {"type": "string", "enum": ["corporate", "guest", "wan", "vlan-only"], "description": "Network purpose/type"},
        "vlan_enabled": {"type": "boolean", "default": False, "description": "Whether VLAN is enabled"},
        "vlan": {"type": "string", "description": "VLAN ID (if VLAN is enabled)"},
        "ip_subnet": {"type": "string", "description": "IP subnet in CIDR notation (e.g., '192.168.1.0/24')"},
        "dhcp_enabled": {"type": "boolean", "default": True, "description": "Whether DHCP is enabled"},
        "dhcp_start": {"type": "string", "description": "Start of DHCP range"},
        "dhcp_stop": {"type": "string", "description": "End of DHCP range"},
        "enabled": {"type": "boolean", "default": True, "description": "Whether the network is enabled"}
    },
    "allOf": [
        {
            "if": {
                "properties": {"vlan_enabled": {"enum": [True]}}
            },
            "then": {"required": ["vlan"]}
        }
    ]
}

# Network update schema
NETWORK_UPDATE_SCHEMA = copy.deepcopy(NETWORK_SCHEMA)
NETWORK_UPDATE_SCHEMA.pop("required", None)
NETWORK_UPDATE_SCHEMA.pop("allOf", None) # Remove conditional requirement for update
# Make all properties optional for update
for prop in NETWORK_UPDATE_SCHEMA.get("properties", {}):
    NETWORK_UPDATE_SCHEMA["properties"][prop].pop("default", None)

# VPN Client Profile schema
VPN_PROFILE_SCHEMA = {
    "type": "object",
    "required": ["name", "server_id"],
    "properties": {
        "name": {"type": "string", "description": "Name for the VPN client profile"},
        "server_id": {"type": "string", "description": "ID of the VPN server"},
        "exp": {"type": "integer", "default": 365, "description": "Expiration in days"}
    }
}

# FirewallPolicy schema
FIREWALL_POLICY_SCHEMA = {
    "type": "object",
    "required": ["name", "ruleset", "action", "rule_index"],
    "properties": {
        "name": {"type": "string", "description": "Name of the firewall policy"},
        "ruleset": {"type": "string", "description": "The firewall ruleset (e.g., 'WAN_IN', 'LAN_OUT')"},
        "action": {"type": "string", "enum": ["accept", "drop", "reject"], "description": "Policy action"},
        "rule_index": {"type": "integer", "description": "Rule index/order (lower numbers process first)"},
        "protocol": {"type": "string", "enum": ["all", "tcp", "udp", "icmp"], "default": "all", "description": "Protocol"},
        "src_address": {"type": "string", "description": "Source address or CIDR"},
        "dst_address": {"type": "string", "description": "Destination address or CIDR"},
        "src_port": {"type": "string", "description": "Source port or range (e.g., '80' or '80-443')"},
        "dst_port": {"type": "string", "description": "Destination port or range (e.g., '80' or '80-443')"},
        "enabled": {"type": "boolean", "default": True, "description": "Whether the policy is enabled"},
        "description": {"type": "string", "description": "Description of the rule"}
    }
}

# Firewall Policy update schema
FIREWALL_POLICY_UPDATE_SCHEMA = copy.deepcopy(FIREWALL_POLICY_SCHEMA)
FIREWALL_POLICY_UPDATE_SCHEMA.pop("required", None)
# Make all properties optional for update
for prop in FIREWALL_POLICY_UPDATE_SCHEMA.get("properties", {}):
    FIREWALL_POLICY_UPDATE_SCHEMA["properties"][prop].pop("default", None)

# Firewall Policy Create schema (V2 API specific)
FIREWALL_POLICY_CREATE_SCHEMA = {
    "type": "object",
    "required": ["name", "ruleset", "action", "index"],
    "properties": {
        "name": {"type": "string", "minLength": 1, "description": "Name of the firewall policy.", "examples": ["Block Xbox LAN Out"]},
        "ruleset": {
            "type": "string", 
            "enum": [ # Based on common UniFi rulesets, adjust if needed
                "WAN_IN", "WAN_OUT", "WAN_LOCAL", 
                "LAN_IN", "LAN_OUT", "LAN_LOCAL", 
                "GUEST_IN", "GUEST_OUT", "GUEST_LOCAL",
                "VPN_IN", "VPN_OUT", "VPN_LOCAL"
            ], 
            "description": "Target firewall ruleset.",
            "examples": ["LAN_OUT"]
        },
        "action": {"type": "string", "enum": ["accept", "drop", "reject"], "description": "Action for matched traffic (must be lowercase).", "examples": ["drop"]},
        "index": {"type": "integer", "minimum": 1, "description": "Rule priority index (lower numbers execute first). API uses 'index' for V2.", "examples": [2010]},
        "enabled": {"type": "boolean", "default": True, "description": "Whether the rule is enabled upon creation.", "examples": [True]},
        "description": {"type": "string", "default": "", "description": "Optional description for the rule.", "examples": ["Block specific Xbox device from WAN"]},
        "logging": {"type": "boolean", "default": False, "description": "Enable logging for matched traffic.", "examples": [True]},
        "protocol": {"type": "string", "default": "all", "description": "Network protocol (e.g., 'tcp', 'udp', 'icmp', 'all').", "examples": ["all"]},
        "connection_state_type": {"type": "string", "enum": ["inclusive", "exclusive"], "default": "inclusive", "description": "How connection states are matched.", "examples": ["inclusive"]},
        "connection_states": {
            "type": "array",
            "items": {"type": "string", "enum": ["new", "established", "related", "invalid"]},
            "default": ["new", "established", "related", "invalid"], # Default to match all states
            "description": "Connection states to match.",
            "examples": [["new", "established", "related", "invalid"]]
        },
        "source": { # Structure based on FirewallPolicyEndpoint TypedDict
            "type": "object",
            "required": ["match_opposite_ports", "matching_target", "port_matching_type", "zone_id"],
            "properties": {
                "match_opposite_ports": {"type": "boolean", "default": False},
                "matching_target": {"type": "string", "enum": ["zone", "client_macs", "network_id", "ip_group_id", "region"], "description": "How source is matched.", "examples": ["client_macs"]},
                "port_matching_type": {"type": "string", "enum": ["any", "single_port", "port_range"], "default": "any", "description": "How ports are matched.", "examples": ["any"]},
                "zone_id": {"type": "string", "description": "Source zone ID (e.g., 'trusted', 'guest', 'iot').", "examples": ["trusted"]},
                "client_macs": {"type": "array", "items": {"type": "string", "format": "mac"}, "description": "Required if matching_target is 'client_macs'.", "examples": [["4c:3b:df:2c:c8:c6"]]}, 
                "network_id": {"type": "string", "description": "Required if matching_target is 'network_id'."}, 
                "ip_group_id": {"type": "string", "description": "Required if matching_target is 'ip_group_id'."}, 
                "port": {"type": "string", "description": "Required if port_matching_type is 'single_port'."}, 
                "port_range_start": {"type": "string", "description": "Required if port_matching_type is 'port_range'."}, 
                "port_range_end": {"type": "string", "description": "Required if port_matching_type is 'port_range'."}, 
                "region": {"type": "string", "description": "Required if matching_target is 'region'."}, 
            },
            "additionalProperties": True # Allow other potential fields
        },
        "destination": { # Structure based on FirewallPolicyEndpoint TypedDict
            "type": "object",
            "required": ["match_opposite_ports", "matching_target", "port_matching_type", "zone_id"],
            "properties": {
                "match_opposite_ports": {"type": "boolean", "default": False},
                "matching_target": {"type": "string", "enum": ["zone", "client_macs", "network_id", "ip_group_id", "region"], "description": "How destination is matched.", "examples": ["zone"]},
                "port_matching_type": {"type": "string", "enum": ["any", "single_port", "port_range"], "default": "any", "description": "How ports are matched.", "examples": ["any"]},
                "zone_id": {"type": "string", "description": "Destination zone ID (e.g., 'wan', 'trusted', 'guest').", "examples": ["wan"]},
                "client_macs": {"type": "array", "items": {"type": "string", "format": "mac"}, "description": "Required if matching_target is 'client_macs'."},
                "network_id": {"type": "string", "description": "Required if matching_target is 'network_id'."},
                "ip_group_id": {"type": "string", "description": "Required if matching_target is 'ip_group_id'."},
                "port": {"type": "string", "description": "Required if port_matching_type is 'single_port'."},
                "port_range_start": {"type": "string", "description": "Required if port_matching_type is 'port_range'."},
                "port_range_end": {"type": "string", "description": "Required if port_matching_type is 'port_range'."},
                "region": {"type": "string", "description": "Required if matching_target is 'region'."},
            },
            "additionalProperties": True # Allow other potential fields
        },
        "icmp_typename": {"type": "string", "description": "ICMP type name (if protocol is 'icmp')."},
        "icmp_v6_typename": {"type": "string", "description": "ICMPv6 type name (if protocol is 'icmpv6')."},
        "ip_version": {"type": "string", "enum": ["ipv4", "ipv6", "both"], "default": "ipv4", "description": "IP version to apply the rule to.", "examples": ["ipv4"]},
        "match_ip_sec": {"type": "boolean", "default": False, "description": "Match IPSec traffic.", "examples": [False]},
        "match_opposite_protocol": {"type": "boolean", "default": False, "description": "Match opposite protocol.", "examples": [False]},
        "schedule": { # Placeholder for schedule object - define if needed
            "type": "object", 
            "properties": {
                 "mode": {"type": "string", "enum": ["always", "specific_time", "disabled"]},
                 "repeat_on_days": {"type": "array", "items": {"type": "string"}}, # e.g., ["mon", "tue"] 
                 "time_all_day": {"type": "boolean"},
                 # Add time_start, time_end if needed for specific_time
            },
            "description": "Rule schedule configuration (optional)."
        },
        "create_allow_respond": {"type": "boolean", "default": False, "description": "Whether to create an allow respond rule automatically.", "examples": [False]},
    },
    "additionalProperties": True # Allow extra fields initially, tighten later
}

# QoS Rule schema
QOS_RULE_SCHEMA = {
    "type": "object",
    "required": ["name", "interface", "direction", "bandwidth_limit_kbps"],
    "properties": {
        "name": {"type": "string", "description": "Descriptive name for the QoS rule"},
        "interface": {"type": "string", "description": "Network interface the rule applies to (e.g., 'WAN', 'LAN')"},
        "direction": {"type": "string", "enum": ["upload", "download"], "description": "Direction of traffic affected"},
        "bandwidth_limit_kbps": {"type": "integer", "description": "Bandwidth limit in Kilobits per second"},
        "target_ip_address": {"type": "string", "description": "Specific IP address to target"},
        "target_subnet": {"type": "string", "description": "Subnet (CIDR notation) to target"},
        "dscp_value": {"type": "integer", "description": "DSCP value to match/set (0-63)", "minimum": 0, "maximum": 63},
        "enabled": {"type": "boolean", "default": True, "description": "Whether the rule is enabled"}
    }
    # Note: UniFi might have more complex targeting (e.g., MAC address, user group) not covered here yet.
}

# QoS Rule update schema
QOS_RULE_UPDATE_SCHEMA = copy.deepcopy(QOS_RULE_SCHEMA)
QOS_RULE_UPDATE_SCHEMA.pop("required", None)
# Make all properties optional for update
for prop in QOS_RULE_UPDATE_SCHEMA.get("properties", {}):
    QOS_RULE_UPDATE_SCHEMA["properties"][prop].pop("default", None)

# Simplified (high-level) QoS Rule schema used by the LLM-friendly create tool
QOS_RULE_SIMPLE_SCHEMA = {
    "type": "object",
    "required": [
        "name",
        "interface",
        "direction",
        "limit_kbps",
    ],
    "properties": {
        "name": {"type": "string", "description": "User-friendly name of the QoS rule"},
        "interface": {
            "type": "string",
            "description": "Target interface (e.g., 'wan', 'lan', 'wan2') – case-insensitive, accepted as displayed in UniFi UI."
        },
        "direction": {"type": "string", "enum": ["upload", "download"], "description": "Traffic direction affected"},
        "limit_kbps": {
            "type": "integer",
            "minimum": 1,
            "description": "Bandwidth limit in kilobits per second (Kbps)"
        },
        "enabled": {"type": "boolean", "description": "Enable rule (default true)"},
        "dscp_value": {
            "type": "integer",
            "minimum": 0,
            "maximum": 63,
            "description": "Optional DSCP value tag (0-63)"
        },
        "target": {
            "type": "object",
            "required": ["type", "value"],
            "description": "Optional traffic selector. If omitted the rule applies to all clients on the interface.",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["ip", "subnet"],
                    "description": "Selector kind: single IP address or subnet CIDR"
                },
                "value": {"type": "string", "description": "Selector value (e.g., '192.168.1.50' or '192.168.1.0/24')"}
            }
        }
    }
}

# Simplified (high-level) Firewall Policy schema used by the LLM-friendly create tool
FIREWALL_POLICY_SIMPLE_SCHEMA = {
    "type": "object",
    "required": [
        "name",
        "ruleset",
        "action",
        "src",
        "dst",
    ],
    "properties": {
        "name": {"type": "string", "description": "User-friendly name of the policy"},
        "ruleset": {
            "type": "string",
            "enum": [
                "WAN_IN", "WAN_OUT", "WAN_LOCAL",
                "LAN_IN", "LAN_OUT", "LAN_LOCAL",
                "GUEST_IN", "GUEST_OUT", "GUEST_LOCAL",
                "VPN_IN", "VPN_OUT", "VPN_LOCAL",
            ],
            "description": "Target firewall ruleset"
        },
        "action": {"type": "string", "enum": ["accept", "drop", "reject"], "description": "Policy action"},
        "src": {
            "type": "object",
            "required": ["type", "value"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["zone", "network", "client_mac", "ip_group"],
                    "description": "Selector type for source"
                },
                "value": {"type": "string", "description": "Selector value (name, id, MAC, etc.)"}
            }
        },
        "dst": {
            "type": "object",
            "required": ["type", "value"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["zone", "network", "client_mac", "ip_group"],
                    "description": "Selector type for destination"
                },
                "value": {"type": "string", "description": "Selector value (name, id, MAC, etc.)"}
            }
        },
        "index": {"type": "integer", "description": "Priority index (optional)"},
        "enabled": {"type": "boolean", "description": "Enable rule (default true)"},
        "log": {"type": "boolean", "description": "Enable logging (default false)"},
        "protocol": {"type": "string", "enum": ["all", "tcp", "udp", "icmp"], "default": "all"}
    }
}

# Simplified (high-level) Port Forward schema used by the LLM-friendly create tool
PORT_FORWARD_SIMPLE_SCHEMA = {
    "type": "object",
    "required": [
        "name",
        "ext_port",
        "to_ip",
    ],
    "properties": {
        "name": {"type": "string", "description": "User-friendly name of the port forward rule"},
        "ext_port": {
            "type": "string",
            "description": "External (destination) port or range, e.g. '80' or '10000-10010'"
        },
        "to_ip": {
            "type": "string",
            "description": "Internal IP address to forward traffic to"
        },
        "int_port": {
            "type": "string",
            "description": "Internal port to forward to (defaults to ext_port if omitted)"
        },
        "protocol": {
            "type": "string",
            "enum": ["tcp", "udp", "both"],
            "description": "Protocol to match (default both)"
        },
        "enabled": {
            "type": "boolean",
            "description": "Enable rule (default true)"
        }
    }
}

class UniFiResourceRegistry:
    """Registry for UniFi Network resource schemas and validators."""
    
    _schemas = {
        "port_forward": PORT_FORWARD_SCHEMA,
        "port_forward_update": PORT_FORWARD_UPDATE_SCHEMA,
        "traffic_route": TRAFFIC_ROUTE_SCHEMA,
        "traffic_route_update": TRAFFIC_ROUTE_UPDATE_SCHEMA,
        "traffic_route_simple": TRAFFIC_ROUTE_SIMPLE_SCHEMA,
        "wlan": WLAN_SCHEMA,
        "wlan_update": WLAN_UPDATE_SCHEMA,
        "network": NETWORK_SCHEMA,
        "network_update": NETWORK_UPDATE_SCHEMA,
        "vpn_profile": VPN_PROFILE_SCHEMA,
        "firewall_policy": FIREWALL_POLICY_SCHEMA,
        "firewall_policy_update": FIREWALL_POLICY_UPDATE_SCHEMA,
        "firewall_policy_create": FIREWALL_POLICY_CREATE_SCHEMA,
        "qos_rule": QOS_RULE_SCHEMA,
        "qos_rule_update": QOS_RULE_UPDATE_SCHEMA,
        "firewall_policy_simple": FIREWALL_POLICY_SIMPLE_SCHEMA,
        "qos_rule_simple": QOS_RULE_SIMPLE_SCHEMA,
        "port_forward_simple": PORT_FORWARD_SIMPLE_SCHEMA
    }
    
    @classmethod
    def get_schema(cls, resource_type: str) -> Dict[str, Any]:
        """Get JSON schema for a resource type."""
        return cls._schemas.get(resource_type, {}) 