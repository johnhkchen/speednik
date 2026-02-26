# Design — T-012-06-BUG-03: slope-adhesion-fails-at-byte-angle-35

## Problem Recap

`build_slope` creates slopes where all tiles sit on a single `ground_row`. At steep angles
(byte angle >= 35, ~49°), the height arrays produced by `_slope_height_array` saturate to
all-zeros because `col_offset` grows faster than the tile can represent. The floor sensors
(now casting rightward in quadrant 1) find nothing, causing on_ground oscillation.

## Option A: Multi-Row Slope Builder

Rewrite `build_slope` to place tiles across multiple rows. As the slope rises, emit tiles
in higher rows with appropriate height arrays. Each tile would cover the portion of the
slope surface that falls within its 16x16 pixel bounds.

**Pros:**
- Physically correct — the tile layout matches the actual slope geometry
- Floor sensors in any quadrant find valid surfaces
- Works for arbitrarily steep angles

**Cons:**
- Significantly more complex builder logic (tracking which row each column falls in)
- Changes the tile grid shape, which could affect test assumptions about slope region bounds
- Need to handle tile boundaries carefully at row transitions

## Option B: Clamp col_offset Per Tile

Modify `_slope_height_array` so that each tile's height array represents only the slope
within that tile's 16-pixel vertical range, ignoring the accumulated offset. Each tile gets
`col_offset=0` (or a value modulo the tile's height range), producing a repeating sawtooth
height profile.

**Pros:**
- Minimal code change
- Height arrays always produce valid 0–16 values

**Cons:**
- Sawtooth produces height discontinuities at tile boundaries
- Doesn't address the fundamental problem (surface spans multiple rows)
- Sensors still may lose tracking at discontinuities

## Option C: Multi-Row Builder with Pixel-Column Tracing (Selected)

Trace the slope surface pixel by pixel (like `build_loop` does for circles), assigning each
pixel to the correct (tx, ty) tile. Compute height contributions per tile. Set tile angles
from the slope. This reuses the proven approach from `build_loop`.

For each pixel column `px` in the slope region:
1. Compute `surface_y = base_y - (px - slope_start) * tan(angle_rad)`
2. Determine tile `(tx, ty)` containing this pixel
3. Set `height_array[local_x] = tile_bottom_y - surface_y`
4. Record the tile angle

Also add fill below each surface tile.

**Pros:**
- Correct for all angles (0–63 byte angles = 0–89°)
- Consistent with `build_loop` approach — proven pattern
- Height arrays always valid (clamped 0–16 per tile)
- Multi-row layout means sensors in any quadrant find valid surfaces

**Cons:**
- Replaces the current `_slope_height_array` indirection with direct pixel tracing
- Slightly more code than current implementation
- Test `slope_start_x` / `slope_end_x` region bounds need pixel-based definition

## Decision: Option C

Option C is the right fix because:

1. It addresses the root cause (single-row limitation) rather than papering over symptoms.
2. It follows the proven `build_loop` pattern already in the codebase, so the approach is
   battle-tested.
3. It produces correct tile layouts for any slope angle up to near-vertical.
4. The test only needs minor adjustment to the slope region bounds (pixel-based rather than
   tile-index-based, but the slope pixel range is still deterministic).

The existing `_slope_height_array` function becomes unused and can be removed.

## Slip System: No Change Needed

The slip system activating at steep angles is by-design (Sonic 2 spec §2.3). Once the
player maintains ground contact on steep slopes, the slip system's behavior becomes correct:
the player slides backward on steep slopes when moving slowly, which is expected gameplay.
The oscillation was caused by sensor failure, not slip logic.

## Test Strategy

- Remove `xfail` marks from `TestSlopeAdhesion` for angles 35–45
- Angles up to 45 byte (~63°) should pass the 80% on_ground threshold
- Very steep angles (> ~63 byte, quadrant 1 deep into wall range) may still have
  legitimately low on_ground due to slip detachment — this is by-design behavior, not a
  sensor bug
- Keep the 80% threshold as the pass/fail criterion

## Scope Boundary

- Only `build_slope` in `grids.py` changes
- `_slope_height_array` is removed (dead code after this change)
- No changes to `terrain.py`, `physics.py`, or `constants.py`
- Test file updates: remove xfail markers, adjust slope region pixel bounds if needed
