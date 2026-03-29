"""Tests for deep_merge utility."""

from unifi_core.merge import deep_merge


class TestDeepMerge:
    """Tests for the deep_merge function."""

    def test_flat_keys_replaced(self):
        base = {"name": "Old", "enabled": True}
        result = deep_merge(base, {"name": "New"})
        assert result == {"name": "New", "enabled": True}

    def test_new_keys_added(self):
        base = {"name": "Test"}
        result = deep_merge(base, {"enabled": False})
        assert result == {"name": "Test", "enabled": False}

    def test_nested_dict_merged_recursively(self):
        base = {
            "name": "Policy",
            "secure": {
                "internet_access_enabled": True,
                "apps": [{"id": "streaming"}],
                "schedule": {"mode": "ALWAYS"},
            },
        }
        result = deep_merge(base, {"secure": {"internet_access_enabled": False}})
        assert result["name"] == "Policy"
        assert result["secure"]["internet_access_enabled"] is False
        assert result["secure"]["apps"] == [{"id": "streaming"}]
        assert result["secure"]["schedule"] == {"mode": "ALWAYS"}

    def test_deeply_nested_merge(self):
        base = {"a": {"b": {"c": 1, "d": 2}, "e": 3}}
        result = deep_merge(base, {"a": {"b": {"c": 99}}})
        assert result == {"a": {"b": {"c": 99, "d": 2}, "e": 3}}

    def test_list_replaces_not_merges(self):
        base = {"members": ["aa:bb:cc:dd:ee:01", "aa:bb:cc:dd:ee:02"]}
        result = deep_merge(base, {"members": ["aa:bb:cc:dd:ee:03"]})
        assert result["members"] == ["aa:bb:cc:dd:ee:03"]

    def test_empty_list_replaces(self):
        base = {"members": ["aa:bb:cc:dd:ee:01"]}
        result = deep_merge(base, {"members": []})
        assert result["members"] == []

    def test_none_replaces(self):
        base = {"schedule": {"mode": "ALWAYS"}}
        result = deep_merge(base, {"schedule": None})
        assert result["schedule"] is None

    def test_empty_updates_preserves_base(self):
        base = {"name": "Test", "config": {"a": 1}}
        result = deep_merge(base, {})
        assert result == base

    def test_base_not_mutated(self):
        base = {"config": {"a": 1, "b": 2}}
        original_config = base["config"].copy()
        deep_merge(base, {"config": {"a": 99}})
        assert base["config"] == original_config

    def test_scalar_replaces_dict(self):
        """When update provides a scalar where base had a dict, replace."""
        base = {"config": {"nested": True}}
        result = deep_merge(base, {"config": "disabled"})
        assert result["config"] == "disabled"

    def test_dict_replaces_scalar(self):
        """When update provides a dict where base had a scalar, replace."""
        base = {"config": "simple"}
        result = deep_merge(base, {"config": {"nested": True}})
        assert result["config"] == {"nested": True}

    def test_real_world_oon_policy(self):
        """Simulate partial OON policy update that triggered this fix."""
        existing = {
            "id": "p1",
            "name": "Kids Bedtime",
            "enabled": True,
            "secure": {
                "internet_access_enabled": True,
                "apps": [{"id": "social_media", "blocked": True}],
                "schedule": {"mode": "SPECIFIC_TIME", "start": "21:00", "end": "07:00"},
            },
            "qos": {"mode": "OFF", "bandwidth_limit": None},
            "route": {"mode": "OFF"},
        }
        updates = {
            "name": "Kids Bedtime v2",
            "secure": {"internet_access_enabled": False},
        }
        result = deep_merge(existing, updates)

        assert result["name"] == "Kids Bedtime v2"
        assert result["secure"]["internet_access_enabled"] is False
        # These must survive:
        assert result["secure"]["apps"] == [{"id": "social_media", "blocked": True}]
        assert result["secure"]["schedule"]["start"] == "21:00"
        assert result["qos"]["mode"] == "OFF"
        assert result["route"]["mode"] == "OFF"

    def test_real_world_acl_traffic_source(self):
        """Simulate partial ACL rule update touching nested traffic_source."""
        existing = {
            "_id": "r1",
            "name": "Allow Pair",
            "traffic_source": {
                "type": "CLIENT_MAC",
                "specific_mac_addresses": ["aa:bb:cc:dd:ee:01"],
                "ips_or_subnets": [],
            },
        }
        updates = {
            "traffic_source": {
                "specific_mac_addresses": ["aa:bb:cc:dd:ee:01", "aa:bb:cc:dd:ee:02"],
            },
        }
        result = deep_merge(existing, updates)

        assert result["traffic_source"]["type"] == "CLIENT_MAC"
        assert len(result["traffic_source"]["specific_mac_addresses"]) == 2
        assert result["traffic_source"]["ips_or_subnets"] == []
