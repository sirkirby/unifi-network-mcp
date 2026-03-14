# BUG-004: List/dict ambiguity in get_network_health()

**Severity:** HIGH
**File:** `src/managers/system_manager.py`
**Line:** 274
**Status:** Done

## Problem

In `get_network_health()`:

```python
health = response if isinstance(response, (list, dict)) else {}
```

The `/stat/health` endpoint can return a list of subsystem dicts. This stores
the raw list in `health` and returns it directly. Callers that expect a dict
will break.

Note: A similar list-response bug was already fixed in `get_system_info()` (commit
a9b2a3f). This is the same class of bug in a different method.

## Fix

Normalize the response consistently. Since health data is naturally a list of
subsystems, the method should either:
1. Always return a list (and document that), or
2. Convert to a dict keyed by subsystem name.

Check what callers (including `diagnosis.py`) actually expect.

## Verification

- Test with both list and dict API responses.
- Verify `diagnosis.py`'s `_summarize_health()` handles the normalized format.
