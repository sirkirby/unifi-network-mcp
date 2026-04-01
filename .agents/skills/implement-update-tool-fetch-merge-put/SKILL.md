---
name: myco:implement-update-tool-fetch-merge-put
description: |
  Use this skill whenever you are implementing or fixing an update_* tool in unifi-mcp. It covers the mandatory fetch-merge-put pattern, deep_merge semantics, V2 API response gotchas, the confirm double-fetch design, LLM UX requirements for dict params, and when flat params are appropriate instead. Applies even if the user only says "add an update tool for X" without specifying the implementation approach — the pattern is required for all update tools in this project.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Implementing an Update Tool: The Fetch-Merge-Put Pattern

All update tools in unifi-mcp follow the **fetch-merge-put** pattern. Skipping the fetch step causes silent data loss — the PUT wipes every field not included in the payload. Five tools shipped with this bug (issue #113) before the pattern was standardized. This skill teaches you how to do it right.

## Prerequisites

- The resource's manager already has a `get_<resource>_by_id` method. If not, write it first (check the V2 API gotcha below before you do).
- `deep_merge` is importable from `unifi-core`. Tests live in `packages/unifi-core/tests/test_merge.py` — run them after any merge logic change.
- The create tool for this resource already exists. Update tools assume the object exists; if it doesn't, the caller should use create, not update.

## Steps

### 1. Read the golden path reference first

Before writing any code, read `network_manager.py:update_network`. It is the canonical implementation of the pattern. Let it orient your mental model before you look at the resource you're adding.

### 2. Implement the four-step pattern

```python
async def update_<resource>(self, resource_id: str, update_data: dict) -> dict:
    # 1. Fetch current state
    current = await self.get_<resource>_by_id(resource_id)
    if not current:
        raise ValueError(f"<Resource> {resource_id} not found")

    # 2. Deep-copy before mutating (protects the cached response)
    import copy
    base = copy.deepcopy(current)

    # 3. Merge caller's partial dict over the base
    merged = deep_merge(base, update_data)

    # 4. PUT the fully-merged object
    return await self._connection.put(f"<endpoint>/{resource_id}", merged)
```

All four steps are required. The deep copy in step 2 is not optional — mutating the cached object in-place corrupts subsequent reads within the same session.

### 3. Understand deep_merge semantics

`deep_merge` has deliberate rules about what it recurses into:

| Value type | Behavior |
|------------|----------|
| `dict` | Merged recursively — sibling keys are preserved |
| `scalar` | Replaced — caller's value wins |
| `list` | Replaced entirely — not element-merged |
| `None` | Replaced — cannot distinguish "clear this field" from "I didn't specify it" |

The list replacement rule is intentional: merging lists would require knowing whether the caller means "append" or "replace," which is ambiguous at the API boundary. If your resource has list fields that need partial updates, document that the caller must pass the full desired list.

### 4. Handle the V2 API response envelope

Some UniFi endpoints (especially newer ones) wrap responses in a `data` list:

```json
{ "data": [ { ...actual object... } ] }
```

If your `get_<resource>_by_id` doesn't unwrap this envelope, `deep_merge` will try to merge against the wrapper dict — the PUT will fail or corrupt data. Check the raw response shape in the controller before assuming the object is at the top level. The fix is to unwrap in the getter:

```python
response = await self._connection.get(f"<endpoint>/{resource_id}")
items = response.get("data", [response])  # normalize both shapes
return items[0] if items else None
```

### 5. Implement the MCP tool with dict params

The MCP tool wrapping the manager method must use a `dict`-typed `update_data` parameter, not individual keyword args. This is an LLM UX requirement: LLMs handle partial updates far better when they can pass a single dict of only what's changing, rather than being forced to specify every field.

```python
@mcp.tool()
async def update_<resource>(
    resource_id: str,
    update_data: dict,
    confirm: bool = False,
) -> str:
    """
    Update a <resource>. Pass only the fields you want to change in update_data.
    The tool fetches current state and merges your changes — fields you omit are preserved.

    Set confirm=True to apply the change, or omit it to preview what would change.
    """
    ...
```

Include the "pass only fields you want to change" language in the docstring. The LLM reads docstrings to understand how to call the tool.

### 6. Implement the confirm preview using a delta, not the merged result

The `confirm=False` preview must show **what is changing**, not the full merged object. The full object is noise — the caller already knows the current state. Show the delta:

```python
if not confirm:
    current = await manager.get_<resource>_by_id(resource_id)
    # Show only the keys the caller is changing
    preview = {k: {"before": current.get(k), "after": v}
               for k, v in update_data.items()}
    return f"Preview (pass confirm=True to apply):\n{json.dumps(preview, indent=2)}"
```

This is a deliberate design decision, not an oversight. The confirm flow does a second fetch (double-fetch) even though the apply path also fetches — that's intentional to ensure the preview reflects live controller state, not stale cache.

### 7. Patch all managers for a new utility

If you're adding or changing merge behavior that affects multiple managers, check `AGENTS.md` for the list of managers that implement update tools. All 11 were patched as part of issue #113. If you're introducing a new shared utility (like `deep_merge` was), update all of them in the same PR — partial patches leave the codebase inconsistent.

## Create vs. Update Asymmetry

Update tools use dict params. Create tools use flat keyword params. This is intentional:

- **Create**: The caller is specifying a complete object from scratch. Flat params with defaults make the required fields clear and the optional ones discoverable.
- **Update**: The caller is expressing a delta. A dict is the natural representation of "change these specific things."

Don't mirror the create tool's signature when building the update tool. They're solving different problems.

## Regression Test Standard

Every update tool must have a test that verifies non-passed fields are preserved after the update. The pattern:

```python
def test_update_preserves_unspecified_fields():
    original = {"name": "original", "vlan": 10, "notes": "keep me"}
    mock_get.return_value = original
    await manager.update_<resource>("id-1", {"name": "new-name"})
    put_payload = mock_put.call_args[1]["json"]
    assert put_payload["vlan"] == 10       # preserved
    assert put_payload["notes"] == "keep me"  # preserved
    assert put_payload["name"] == "new-name"  # updated
```

This test pattern catches the original bug class (PUT without fetch) at the test level.
