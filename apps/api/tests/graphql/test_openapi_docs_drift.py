"""CI gate: openapi-reference.md matches the docgen render."""

from pathlib import Path

from unifi_api.graphql.docgen import render_openapi_reference

REF_PATH = Path(__file__).resolve().parents[2] / "docs" / "openapi-reference.md"


def test_openapi_reference_matches_render() -> None:
    expected = render_openapi_reference().strip()
    actual = REF_PATH.read_text(encoding="utf-8").strip()
    assert actual == expected, (
        "openapi-reference.md is stale. Re-generate with:\n"
        "  uv run --package unifi-api python -m unifi_api.graphql.docgen\n"
    )
