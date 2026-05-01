"""Auto-generate apps/api/docs/graphql-reference.md from the SDL.

Run: `uv run --package unifi-api python -m unifi_api.graphql.docgen`
to regenerate. CI gate (test_docs_drift) catches staleness.
"""

from __future__ import annotations

from pathlib import Path

from unifi_api.graphql.schema import schema


HEADER = """# unifi-api GraphQL Reference

> Auto-generated from the Strawberry schema by `unifi_api.graphql.docgen`.
> Do not edit by hand. Regenerate with `python -m unifi_api.graphql.docgen`.

"""


def render_reference() -> str:
    """Render the markdown reference from the schema's SDL."""
    sdl = str(schema).strip()
    return (
        HEADER
        + "## Schema (SDL)\n\n```graphql\n"
        + sdl
        + "\n```\n"
    )


def main() -> None:
    out_path = Path(__file__).resolve().parents[3] / "docs" / "graphql-reference.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_reference(), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
