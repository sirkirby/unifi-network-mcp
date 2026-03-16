"""Network server permission category mappings.

Maps tool category shorthands to their config key names used in
the permissions section of config.yaml. This mapping is injected into
the shared PermissionChecker at startup.
"""

# Mapping from tool category shorthand to config key
NETWORK_CATEGORY_MAP = {
    "firewall": "firewall_policies",
    "qos": "qos_rules",
    "vpn_client": "vpn_clients",
    "vpn_server": "vpn_servers",
    "vpn": "vpn",
    "network": "networks",
    "wlan": "wlans",
    "device": "devices",
    "client": "clients",
    "guest": "guests",
    "traffic_route": "traffic_routes",
    "port_forward": "port_forwards",
    "event": "events",
    "voucher": "vouchers",
    "usergroup": "usergroups",
    "route": "routes",
    "snmp": "snmp",
    "acl": "acl_rules",
}
