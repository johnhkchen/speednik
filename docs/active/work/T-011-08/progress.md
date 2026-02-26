# T-011-08 Progress: Extract Shared Code from Tests

## Completed

### Step 1: Created `speednik/grids.py`
- Copied full content of `tests/grids.py` (380 lines) to `speednik/grids.py`.
- Updated module docstring to reflect new role as production code.
- Verified: `from speednik.grids import build_flat, build_loop, build_ramp, FILL_DEPTH` succeeds.

### Step 2: Created `speednik/strategies.py`
- Copied full content of `tests/harness.py` (271 lines) to `speednik/strategies.py`.
- Updated module docstring to reflect new location and role.
- Verified: `from speednik.strategies import hold_right, run_scenario, Strategy, FrameSnapshot` succeeds.

### Step 3: Converted `tests/grids.py` to re-export shim
- Replaced 380-line implementation with 2-line re-export: `from speednik.grids import *`
- Verified: `from tests.grids import build_flat, FILL_DEPTH` still works via shim.

### Step 4: Converted `tests/harness.py` to re-export shim
- Replaced 271-line implementation with 2-line re-export: `from speednik.strategies import *`
- Verified: `from tests.harness import hold_right, FrameSnapshot` still works via shim.

### Step 5: Updated imports in `speednik/devpark.py`
- Changed all 13 lazy import statements:
  - 5× `from tests.grids import` → `from speednik.grids import`
  - 8× `from tests.harness import` → `from speednik.strategies import`
- Verified: `from speednik.devpark import STAGES` succeeds, all 7 stages load.

### Step 6: Full test suite
- `uv run pytest tests/ -x` → 1212 passed, 16 skipped, 5 xfailed. All green.

### Step 7: Runtime verification
- `from speednik.devpark import STAGES` works outside pytest context.
- All re-export shims work for both `tests.grids` and `tests.harness` imports.

## Deviations from Plan

None. All steps executed as planned.
