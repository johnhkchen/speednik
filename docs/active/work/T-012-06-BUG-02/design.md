# Design: T-012-06-BUG-02 — large-loop-exit-overshoot

## Problem Restatement

The player detaches from the loop surface during the Q2→Q3 transition (ceiling
to left wall) for loops with radius >= 64. After detaching, the player falls
backward and never reaches the exit tiles. A secondary issue is that even after
fixing detachment, r=96 overshoots the exit flat tiles due to insufficient
landing zone coverage.

## Root Cause

### Primary: `_sensor_cast_up()` height==0 blind spot

When a tile exists but has `height_array[col] == 0` at the sensor column, the
function only checks tile above. It does not check tile below, missing the
ceiling surface that may be in the adjacent tile.

Specific scenario (r=64, f46): sensor A at (293.6, 207.8) is in tile (18,12)
which exists with h[5]=0. Tile (18,13) has the surface at y=208, just 0.2px
below the sensor.

### Secondary: Insufficient exit tile coverage

`build_loop()` adds `approach_tiles` (15) flat exit tiles. For r=96, the player
exits the loop with a high-speed ballistic arc that requires ~35 tiles of
landing zone.

## Decision: Two-part fix

### Fix 1: Add tile-below fallback in `_sensor_cast_up` height==0 branch

When current tile has h[col]=0, after checking tile above, also check tile
below. This mirrors the existing tile-below regression check in the height==16
branch.

**Pros**: Directly fixes the blind spot; ~10 lines; mirrors existing pattern.
**Cons**: Adds another conditional path to sensor code.

### Fix 2: Scale exit tiles by radius

Change the exit tile count from `approach_tiles` to
`approach_tiles + 2 * ceil(radius / TILE_SIZE)`. This ensures larger loops
get proportionally more landing zone.

**Pros**: Simple formula; scales correctly for any radius.
**Cons**: Slightly more tiles generated for large loops.

## Impact Assessment

- terrain.py: sensor fix is confined to `_sensor_cast_up()`, no changes to
  public interface
- grids.py: exit tile count change only affects `build_loop()`, no changes to
  other builders
- No changes to physics, player logic, or loop circle geometry
- r=128 loop trapping remains as a separate, out-of-scope issue
