"""Controller-supported transitions for inverted port matches."""

import pytest
from unifi_core.network.models.firewall import (
    normalize_policy_update,
    prepare_policy_update,
    validate_policy_selectors,
)


@pytest.mark.parametrize("mode,selector", [("SPECIFIC", {"port": "53"}), ("OBJECT", {"port_group_id": "ports"})])
def test_disabling_port_matching_clears_inversion_and_retires_selector(mode, selector):
    current = {
        "destination": {"port_matching_type": mode, "match_opposite_ports": True, **selector},
    }
    update = prepare_policy_update(current, {"destination": {"port_matching_type": "ANY"}})
    assert update["destination"]["match_opposite_ports"] is False
    assert update["destination"][next(iter(selector))] is None
    assert current["destination"]["match_opposite_ports"] is True


@pytest.mark.parametrize("validate", [validate_policy_selectors, normalize_policy_update])
def test_explicit_any_port_inversion_is_rejected(validate):
    with pytest.raises(ValueError, match="match_opposite_ports must be false"):
        validate({"destination": {"port_matching_type": "ANY", "match_opposite_ports": True}})
