# T-011-08 Plan: Extract Shared Code from Tests

## Step 1: Create `speednik/grids.py`

Copy full content of `tests/grids.py` to `speednik/grids.py`. Update the module docstring
from "Synthetic tile-grid builders for physics tests" to "Synthetic tile-grid builders for
physics scenarios and dev park." All imports, constants, helpers, and builders are identical.

**Verify:** `python -c "from speednik.grids import build_flat, build_loop, build_ramp"` succeeds.

## Step 2: Create `speednik/strategies.py`

Copy full content of `tests/harness.py` to `speednik/strategies.py`. Update the module
docstring to reflect the new location. All types, dataclasses, helpers, runners, and
strategy factories are identical.

**Verify:** `python -c "from speednik.strategies import hold_right, run_scenario, Strategy"` succeeds.

## Step 3: Convert `tests/grids.py` to re-export shim

Replace entire file content with:
```python
"""Re-export shim — canonical location is speednik.grids."""
from speednik.grids import *  # noqa: F401,F403
```

**Verify:** `python -c "from tests.grids import build_flat, FILL_DEPTH"` still works.

## Step 4: Convert `tests/harness.py` to re-export shim

Replace entire file content with:
```python
"""Re-export shim — canonical location is speednik.strategies."""
from speednik.strategies import *  # noqa: F401,F403
```

**Verify:** `python -c "from tests.harness import hold_right, FrameSnapshot"` still works.

## Step 5: Update imports in `speednik/devpark.py`

Find-and-replace all 13 lazy import statements:
- `from tests.grids import` → `from speednik.grids import`
- `from tests.harness import` → `from speednik.strategies import`

No changes to imported names, function calls, or surrounding code.

**Verify:** `python -c "from speednik.devpark import make_bots_for_stage"` succeeds (module
parses, lazy imports not triggered).

## Step 6: Run full test suite

```bash
uv run pytest tests/ -x
```

All tests must pass. If any fail, diagnose — likely a missed import or re-export issue.

## Step 7: Verify dev park runtime launch

```bash
SPEEDNIK_DEBUG=1 uv run python -c "from speednik.devpark import STAGES; print([s.name for s in STAGES])"
```

This exercises the import chain without requiring Pyxel display. Verifies that devpark can
load and the stage definitions reference the new modules correctly.

## Testing Strategy

- **No new tests needed.** This is a pure refactoring — code moves, behavior doesn't change.
- **Existing tests are the verification.** All 8 test files continue importing from
  `tests.grids` and `tests.harness` via re-export shims. If shims work correctly, tests pass.
- **Runtime verification:** The dev park launch check (Step 7) covers the primary bug —
  `ModuleNotFoundError` when running outside pytest.
- **Import verification:** Steps 1-5 each have a quick `python -c` check that the import
  resolves, catching issues before the full test suite runs.

## Commit Strategy

Single atomic commit containing all changes:
- 2 new files: `speednik/grids.py`, `speednik/strategies.py`
- 2 modified files (shims): `tests/grids.py`, `tests/harness.py`
- 1 modified file (imports): `speednik/devpark.py`

All changes are interdependent — partial application would break imports.
