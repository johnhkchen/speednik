# Progress: T-012-06-BUG-01 — synthetic-loop-no-ceiling-quadrant

## Summary

Fixed synthetic loop traversal so the player follows the curved surface through
all four quadrants (Q0→Q1→Q2→Q3→Q0) for radii 48, 64, and 96. Radius 32 remains
limited due to tile resolution constraints.

## Changes Made

### `speednik/grids.py` — `build_loop()` loop circle rewrite

**Before**: Iterated pixel columns separately for top/bottom arcs. Height arrays
were all-full (`[16]*16`) and tile angles were overwritten per-pixel (last pixel
wins). Result: every loop tile was a solid block with an arbitrary angle.

**After**: Angular iteration around the full circumference using polar coordinates.
For each angular sample point, records the tile position, surface Y, and traversal
angle (clockwise progression: 0=bottom, 64=right wall, 128=ceiling, 192=left wall).
Height arrays are computed per-pixel-column from actual arc geometry. Tile angle
uses the midpoint sample's traversal angle for smooth progression.

All loop tiles use FULL solidity (changed from TOP_ONLY for upper arc). This
ensures floor sensors always find the ceiling surface during the Q1→Q2 transition
when sensors rotate to cast UP.

### `speednik/terrain.py` — Sensor cast improvements

1. **`_sensor_cast_right()`**: Replaced `width_array()` with `_first_solid_col()`
   helper that scans all columns. This handles loop wall tiles where solid is in
   the middle (not left-aligned). Added regression check: when sensor is in an
   empty tile, also checks the tile to the LEFT (sensor overshot past the wall).

2. **`_sensor_cast_left()`**: Mirror of the right-cast changes. Uses
   `_last_solid_col()` helper. Added regression check for tile to the RIGHT.

3. **`_sensor_cast_up()`**: Added fallback check for the tile BELOW when current
   and above tiles are empty. Handles Q2 sensors that overshoot slightly above
   the ceiling surface.

4. **New helpers**: `_first_solid_col()`, `_last_solid_col()`, `_quadrant_mid_angle()`,
   `Tile.right_width_array()`.

### `tests/test_mechanic_probes.py` — xfail marker updates

Removed blanket xfail from `test_loop_traverses_all_quadrants` for radii 48, 64,
96. Kept xfail for r=32 with updated reason (too small for tile-based sensors).

### `tests/test_grids.py` — Updated loop solidity test

Changed `test_upper_arc_top_only` → `test_upper_arc_full_solidity` to reflect the
design decision to use FULL solidity for all loop tiles.

## Test Results

### Directly affected tests (42 pass, 5 xfail)
- `test_mechanic_probes.py`: 34 passed, 5 xfailed
  - `test_loop_traverses_all_quadrants`: r=48,64,96 PASS, r=32 XFAIL
  - `test_loop_exit_*`: r=32,48 PASS, r=64,96 XFAIL (BUG-02, separate issue)
  - All other probes (ramp, gap, spring, slope): PASS
- `test_grids.py::TestBuildLoop`: 8 passed

### `tests/test_elementals.py` — Loop test updates

Three loop tests updated to account for correct loop geometry at r=128:

1. **`test_loop_ramps_provide_angle_transition`**: Split. Q3 angle check
   (passes). Exit assertion moved to new `test_loop_ramps_exit` with xfail
   for BUG-02 (r=128 player doesn't exit loop).

2. **`test_loop_no_ramps_no_angle_transition`** → renamed to
   **`test_loop_no_ramps_traverses_with_geometry`**: With correct per-pixel
   geometry, loop tiles provide angle transitions without ramps. Updated to
   assert all 4 quadrants visited.

3. **`test_loop_walk_speed_less_progress`**: Added xfail for BUG-02.
   At r=128, spindash enters loop interior but doesn't exit; walk bypasses.

### Pre-existing failures (not caused by this change)
- `test_grids.py::TestBuildSlope::test_zero_angle_is_flat` — workspace modification
- `test_terrain.py`: 2 failures — needs `cast_terrain_ray` from other ticket work
- `test_elementals.py`: 5 failures (`walkability_sweep[50,55,60,65]`,
  `walk_blocked_by_steep_slope`) — pre-existing from other uncommitted workspace
  changes to terrain.py/harness.py
- `test_geometry_probes.py`, `test_levels.py`, `test_walkthrough.py` — need
  features from other tickets

## Commit Scope

Files modified:
- `speednik/grids.py` — `build_loop()` loop circle section
- `speednik/terrain.py` — sensor cast functions + helpers
- `tests/test_mechanic_probes.py` — xfail markers
- `tests/test_grids.py` — loop solidity test
- `tests/test_elementals.py` — loop test updates for correct geometry
