# Design: T-012-06-BUG-01 — synthetic-loop-no-ceiling-quadrant

## Approach Options

### Option A: Fix `build_loop()` geometry only

Fix the height arrays and angle assignments in `build_loop()` so each tile has
per-pixel-column height data that accurately represents the circle arc, plus a
representative angle (e.g., the midpoint angle across the tile's arc span).

**Pros**: Minimal code change, contained in `grids.py`, no engine changes needed.
**Cons**: May not fully solve the problem if the snap tolerances can't track the
curvature at small radii. Does not fix the TOP_ONLY solidity issue.

### Option B: Fix geometry + change upper arc solidity from TOP_ONLY to FULL

Same as Option A, but also change the upper arc tiles to `solidity=FULL` instead of
`TOP_ONLY`. This ensures floor sensors always see the ceiling surface.

**Pros**: Solves the Q1->Q2 transition where floor sensors reject TOP_ONLY tiles.
**Cons**: If upper tiles are FULL, the player cannot jump through the bottom of the
loop to enter it from below. But synthetic loops are entered from the side via ramps,
so this isn't a real concern for `build_loop()`.

### Option C: Fix geometry + add centripetal force to physics engine

Add a centripetal lock when the player is on SURFACE_LOOP tiles: force the player to
stay attached regardless of snap distance.

**Pros**: Most robust -- handles any radius.
**Cons**: Over-engineered. Adds loop-specific physics logic to the general engine.
Changes the physics model in ways that may affect other mechanics. The original Sonic 2
engine does NOT use centripetal force -- it relies entirely on sensors and geometry.

### Option D: Fix geometry + increase snap distance for SURFACE_LOOP tiles

Increase `_GROUND_SNAP_DISTANCE` or `MAX_SENSOR_RANGE` specifically when on loop tiles.

**Pros**: Targeted fix, keeps the general sensor model intact.
**Cons**: Magic numbers. Snap distance isn't the real problem -- the problem is that
the geometry is wrong. If the geometry accurately represents the circle, the existing
14px snap distance should be sufficient for reasonable radii.

## Decision: Option B — Fix geometry + FULL solidity for upper arc

### Rationale

The root cause is clearly in `build_loop()`. The geometry is fundamentally broken:
all-full height arrays with single overwritten angles. Fixing the geometry is both
necessary and likely sufficient.

The TOP_ONLY -> FULL change for upper arc tiles is the right pragmatic choice:

1. `build_loop()` creates loops entered via side ramps, not from below. The player
   never needs to jump up through the bottom half.
2. When on the right wall (Q1) transitioning to ceiling (Q2), the floor sensors
   rotate to cast UP. If ceiling tiles are TOP_ONLY, the `_floor_solidity_filter`
   rejects them when `y_vel < 0`. With FULL solidity, they're always visible.
3. The existing wall sensor exemption (`find_wall_push` returns False for SURFACE_LOOP)
   already prevents loop tiles from blocking horizontal movement.

Option C is rejected because the Sonic 2 engine design principle is geometry-driven
collision, not force-based. If we get the geometry right, the existing sensor system
handles it.

Option D is rejected because increased snap distance is a band-aid. The 14px snap
tolerance is generous enough for a circle where adjacent tiles differ by at most one
tile row (16px) in surface position.

## Geometry Fix Details

### Height arrays: compute per-pixel arc position within each tile

For each pixel column in a loop tile, compute the actual Y position of the circle
arc at that column, then convert to a height value relative to the tile:

```
height[col] = max(0, min(16, tile_bottom - arc_y_at_col))
```

For the **bottom arc**, surface is at `cy + sqrt(r^2 - dx^2)`. The height is measured
from the bottom of the tile upward.

For the **top arc**, surface is at `cy - sqrt(r^2 - dx^2)`. The height array represents
how much solid exists from the bottom of the tile. For ceiling tiles, the solid part
is above the surface, so:
```
height[col] = max(0, min(16, arc_y_at_col - tile_top))
```

This gives the sensor system sub-tile precision to track the curved surface.

### Angles: use per-tile midpoint angle

Instead of overwriting the tile angle with each pixel, compute the angle at the
midpoint of the tile's arc span:

```python
mid_px = tile_x * TILE_SIZE + TILE_SIZE // 2
dx_mid = mid_px - cx + 0.5
dy_mid = sqrt(r^2 - dx_mid^2)
angle = round(-atan2(dx_mid, dy_mid) * 256 / (2*pi)) % 256
```

This gives a representative angle for the tile that is smooth from tile to tile.

### Upper arc: FULL solidity + SURFACE_LOOP tile_type

Upper arc tiles get `solidity=FULL` (not TOP_ONLY) and `tile_type=SURFACE_LOOP`.
The SURFACE_LOOP tile_type already provides the necessary exemptions:
- Wall sensors ignore them
- Solid ejection skips them
- The `_check_inside_solid` invariant skips them

### Fill tiles between arcs

Currently `build_loop()` only fills below the bottom arc. The interior between arcs
should remain empty (no tiles) so the player can traverse through it.

## Rejected Alternatives

- **Averaging angles across tile**: Would still produce jumps at tile boundaries.
  Midpoint angle is cleaner and what the original Sonic 2 engine uses.
- **Interpolating height arrays between tiles**: Over-complicated. Per-pixel circle
  evaluation is straightforward and geometrically exact.
- **Sub-tile collision system**: Major engine refactor, out of scope for a bug fix.

## Risk Assessment

- **Low risk**: Changes are isolated to `build_loop()` in `grids.py`. No engine
  changes. No changes to `terrain.py`, `physics.py`, or `simulation.py`.
- **Test coverage**: `test_loop_traverses_all_quadrants` xfail markers should be
  removable for working radii. The xfail tests become the acceptance criteria.
- **Regression**: The flat approach, exit ramp, and exit tiles are unchanged.
  Existing passing tests (`test_loop_exit_positive_speed` for r=32,48) must continue
  to pass.
