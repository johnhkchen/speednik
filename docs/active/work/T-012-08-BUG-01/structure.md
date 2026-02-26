# Structure: T-012-08-BUG-01 — Hillside Loop Not Traversable

## Overview

Replace the hillside loop collision tiles (tile_map.json and collision.json)
with synthetically generated loop geometry using the same algorithm as
`build_loop()` in `speednik/grids.py`. No changes to the physics engine,
sensor system, or any Python source files besides possibly a one-time
data generation script.

## Files Modified

### `speednik/stages/hillside/tile_map.json`
- **What changes**: Loop region tiles (approximately tx=214-235, ty=23-39)
  are replaced with synthetically generated tiles that have:
  - Smooth angle progressions through all four quadrants
  - Height arrays that match the angular curvature
  - tile_type=5 (SURFACE_LOOP) for loop arc tiles
  - tile_type=1 for approach/exit ramp tiles
- **Preserved**: All tiles outside the loop region remain unchanged.
  The flat ground tiles at ty=39-44 inside the loop are preserved (they
  form the inner floor that the player rides through at the bottom).

### `speednik/stages/hillside/collision.json`
- **What changes**: Solidity values for the replaced tiles. Loop arc tiles
  get solidity=2 (FULL). The existing top-arc tiles that had solidity=1
  (TOP_ONLY) will be replaced with FULL-solidity loop tiles.
- **Preserved**: All non-loop solidity values unchanged.

### `tests/test_loop_audit.py`
- **What changes**: Remove the `xfail` markers on `TestHillsideLoopTraversal`
  tests (`test_all_quadrants_grounded` and `test_exits_loop_region`).
  These tests should now pass with the fixed tile data.

## Files NOT Modified

- `speednik/terrain.py` — No sensor/collision logic changes
- `speednik/physics.py` — No movement/slope changes
- `speednik/grids.py` — build_loop() is used as reference but not modified
- `speednik/level.py` — Loading logic unchanged
- `speednik/player.py` — Player logic unchanged
- `speednik/constants.py` — No constant changes

## Data Generation Approach

The replacement tiles will be generated using a script that:

1. **Determines loop parameters** from existing tile positions:
   - Center X: midpoint of left wall (tx=217) and right wall (tx=232) columns
     = pixel (217+232)/2 * 16 + 8 ≈ 3600
   - Center Y: midpoint of top (ty=23) and bottom (ty=39) tile rows. But the
     loop is not centered vertically — the bottom is at the ground. Using the
     build_loop() convention: cy = ground_y - radius.
   - Ground row: ty=39 (where the inner floor tiles are)
   - Radius: estimated from the arc span. The loop spans from ty≈23 to ty≈39,
     which is 16 tile rows = 256 pixels. Radius ≈ 128 pixels.

2. **Generates loop tiles** using the build_loop() angular sampling algorithm:
   - Sub-pixel angular sampling around the full circumference
   - For each sample point, compute (tx, ty, local_x, surface_y, traversal_angle)
   - Build height arrays and angles per tile
   - Set tile_type=SURFACE_LOOP, solidity=FULL

3. **Generates approach/exit ramps** using quarter-circle arcs (same as
   build_loop()'s ramp logic), connecting the ground surface to the loop entry

4. **Merges** the generated tiles into the existing tile_map.json and collision.json,
   replacing only tiles within the loop region bounding box

## Testing Strategy

- Primary: `test_loop_audit.py::TestHillsideLoopTraversal` — both tests must pass
- Secondary: `test_levels.py` — existing stage loading tests must still pass
- Tertiary: Full test suite run to check for regressions

## Risks

- The synthetic loop radius/center may not perfectly align with the visual sprite
  tiles, causing a visual-collision mismatch. This is acceptable since collision
  accuracy is more important than pixel-perfect visual alignment for gameplay.
- The approach/exit ramp tiles may overlap with non-loop terrain features. The
  merge step must preserve non-loop tiles outside the replacement region.
