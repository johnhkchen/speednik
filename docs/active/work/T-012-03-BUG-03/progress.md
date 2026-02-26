# Progress — T-012-03-BUG-03: pipeworks-chaos-early-clipping

## Completed

### Step 1: Add horizontal ejection fallback in `_eject_from_solid()`

Modified `speednik/terrain.py` function `_eject_from_solid()`:
- Added horizontal ejection between the upward scan loop and the final fallback.
- After the upward scan exhausts `_EJECT_SCAN_TILES=8` without finding free space,
  scans left and right from the player's column within the current tile.
- Alternates left/right at increasing distance (dc=1,2,...,15) to find the nearest
  empty column.
- On success: sets `state.x` to the free column, airborne, zero velocity.
- On failure: falls through to existing `y -= TILE_SIZE` fallback.

### Step 2: Add unit test for horizontal ejection

Added `test_eject_from_solid_horizontal()` in `tests/test_terrain.py`:
- Creates 12-tile-tall thin wall column (only col 4 solid, h=[0,0,0,0,16,0,...,0]).
- Places player center on the solid column inside the tile.
- Asserts `resolve_collision()` ejects player horizontally (col != 4 after).
- Asserts player is airborne with zero velocity after ejection.

### Step 3: Run full test suite

All 1284 tests pass, 17 skipped, 18 xfailed. No regressions.

### Step 4: Run pipeworks chaos audit

Chaos (seed=42) now produces **0 invariant errors** (was 2 before fix).
Only remaining finding: max_x≈429 < 800 target (progress shortfall, not a
collision bug).

### Step 5: Update test xfail

Updated `test_pipeworks_chaos` xfail reason to remove BUG-03 reference:
- Old: "BUG: T-012-03-BUG-03 solid clipping at x≈100 + insufficient progress"
- New: "Chaos max_x≈429 below 800 target (BUG-03 clipping fixed, progress shortfall remains)"

## Deviations from Plan

None.
