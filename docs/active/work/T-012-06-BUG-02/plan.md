# Plan: T-012-06-BUG-02 — large-loop-exit-overshoot

## Step 1: Fix `_sensor_cast_up()` — Add tile-below fallback in height==0 branch

**File**: `speednik/terrain.py`, function `_sensor_cast_up()`

**What**: In the `height == 0` branch, after checking tile above and before
returning found=False, add a check for the tile below. This mirrors the
existing tile-below regression check in the height==TILE_SIZE branch.

**Verification**: r=64 and r=96 players traverse all 4 quadrants (Q0-Q3).

## Step 2: Fix exit tile count in `build_loop()`

**File**: `speednik/grids.py`, function `build_loop()`

**What**: Scale exit tile count by radius so large loops have adequate landing
zone. Formula: `approach_tiles + 2 * ceil(radius / TILE_SIZE)`.

**Verification**: r=96 player lands on exit tiles after loop traversal.

## Step 3: Verify loop traversal and exit for all radii

**Command**: `uv run pytest tests/test_mechanic_probes.py -k loop -v`

**Expected**: All loop tests pass (with xfail markers removed in step 4).

## Step 4: Update xfail markers

**Files**: `tests/test_mechanic_probes.py`, `tests/test_elementals.py`

- Remove xfail from `test_loop_traverses_all_quadrants` (all 4 radii)
- Update xfail reasons in `test_elementals.py` for r=128 loop-trapping tests

## Step 5: Run full test suite for regression

**Command**: `uv run pytest tests/test_mechanic_probes.py -v`

**Expected**: All 39 tests pass. No regressions in ramp, gap, spring, or
slope tests.

## Commit scope

Single commit modifying:
- `speednik/terrain.py` (~10 lines added)
- `speednik/grids.py` (~3 lines changed)
- `tests/test_mechanic_probes.py` (xfail marker removals)
- `tests/test_elementals.py` (xfail reason updates)
