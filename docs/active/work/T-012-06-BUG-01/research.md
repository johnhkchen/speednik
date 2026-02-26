# Research: T-012-06-BUG-01 — synthetic-loop-no-ceiling-quadrant

## Problem Statement

`build_loop()` synthetic loops cannot be fully traversed. The player enters the loop
ramp (quadrant 1) but goes airborne instead of following the curve through the
ceiling (quadrant 2). Quadrant 2 is never reached for any tested radius (32, 48, 64, 96).

## Architecture: How Loop Traversal Should Work

The engine has no explicit centripetal force. Loop traversal relies on:

1. **Angle-aware movement** (`physics.py:262`): `ground_speed` decomposes via
   `cos(angle)/sin(angle)` so the player follows the surface tangent direction.
2. **Quadrant-rotated sensors** (`terrain.py:532-578`): `find_floor()` rotates sensor
   positions and cast direction by quadrant (Q0=DOWN, Q1=RIGHT, Q2=UP, Q3=LEFT).
3. **Two-pass snapping** (`terrain.py:848-852`): When a floor snap changes the quadrant,
   `resolve_collision` immediately re-runs the floor sensor with the new direction.
4. **SURFACE_LOOP exemptions** (`terrain.py:675,754`): Loop tiles are invisible to wall
   sensors and solid-ejection, preventing the player from getting stuck.
5. **Slope factor** (`physics.py:223`): `ground_speed -= factor * sin(angle)` per frame
   decelerates uphill and accelerates downhill.

## Key Constants

- `_GROUND_SNAP_DISTANCE = 14.0` (max floor snap while on ground)
- `_AIR_LAND_DISTANCE = 16.0` (max distance for airborne landing)
- `MAX_SENSOR_RANGE = 32` (single sensor cast max)
- `TILE_SIZE = 16`
- `SPINDASH_BASE_SPEED = 8.0` (initial spindash velocity)
- `ROLLING_HEIGHT_RADIUS = 14`, `ROLLING_WIDTH_RADIUS = 7`

## Root Cause Analysis

### Problem 1: `build_loop()` sets all height_arrays to `[TILE_SIZE]*16` (all-full)

In `grids.py:301` (bottom arc) and `grids.py:318` (top arc):
```python
tiles[key_b].height_array[local_x] = TILE_SIZE  # always 16
```

Every loop tile gets `height_array = [16, 16, ..., 16]`. This means **every pixel
column reports surface at the top of the tile**. The sensor system cannot distinguish
the curved surface position within a tile -- every column reports the same height.

For a radius-48 loop, the circle occupies ~6 tile-rows vertically. The actual surface
position varies smoothly across each tile, but the height array says "top of tile"
everywhere. When the player moves rightward into the right wall of the loop (Q1 transition),
the RIGHT-cast sensors look for the left edge of solid in the tile. With `[16]*16`,
`width_array()` returns `[16]*16` (all full), so `surface_x = tile_x * TILE_SIZE`.
The sensor sees the surface at the left edge of the tile, which is correct for a
fully-solid tile but gives no curvature information.

The consequence: the player snaps to tile boundaries rather than following the arc,
and the large angular jumps between adjacent tiles exceed the snap tolerance, causing
detachment.

### Problem 2: Per-tile angle overwrites

In `grids.py:302` and `grids.py:319`:
```python
tiles[key_b].angle = angle_bottom
```

Each pixel column writes `angle_bottom` to the tile's single `angle` field. Since the
loop iterates left-to-right, the final pixel in each tile wins. A tile spanning 16px
of the circle arc may have angles ranging across 20-30 byte-angle units, but only the
rightmost pixel's angle is stored.

This creates **discontinuous angle transitions** at tile boundaries. The player sees
angle A at one tile, then jumps to angle B at the next, where |B - A| could be 20-30
units. When this jump crosses a quadrant boundary, the two-pass mechanism triggers,
but the sensor directions change so drastically that the floor sensor may not find
the surface at all (it's now casting in a completely different direction and the surface
is not within `_GROUND_SNAP_DISTANCE`).

### Problem 3: TOP_ONLY solidity filter interaction

Upper arc tiles get `solidity = TOP_ONLY` (`grids.py:332`). The floor solidity filter
(`terrain.py:501-507`) rejects TOP_ONLY tiles when `y_vel < 0` (moving upward). When
the player is traversing upward through Q1, `y_vel` is negative (moving up in screen
coords). This means the ceiling tiles are **invisible to floor sensors** during the
exact moment the player needs to transition from the right wall to the ceiling.

### Problem 4: No per-pixel height precision in sensor casts

`_sensor_cast_right` (`terrain.py:333-404`) uses `width_array()` which is derived from
`height_array`. With `height_array = [16]*16`, `width_array()` returns `[16]*16`,
meaning every row reports 16px of solid from the left edge. The surface distance
computation becomes `surface_x = tile_x * TILE_SIZE + (TILE_SIZE - 16) = tile_x * TILE_SIZE`.
The sensor always snaps to the tile's left edge, providing no sub-tile precision.

## How the Hillside Loop Differs

The hillside stage hand-places tiles with **shallow, per-tile height arrays** (max 4px
per tile) and gentle angles near flat (5, 251, 246). It doesn't actually achieve true
loop traversal either -- the test in `test_geometry_probes.py` only checks for Q1 entry,
not full Q2 ceiling traversal. The hillside "loop" is more of a visual decoration than
a functional loop.

## Tests Documentation

- `test_mechanic_probes.py:263-269`: `test_loop_traverses_all_quadrants` is `xfail` for
  all radii, explicitly documenting this bug.
- `test_mechanic_probes.py:283-294`: `test_loop_exit_positive_speed` passes for r=32,48
  (player flies over the loop and lands on exit flat) but xfails for r=64,96.
- `test_elementals.py:196-220`: Tests ramp-based loops with r=128, only checks Q3 not Q2.

## Summary of Root Causes

| # | Cause | Location | Effect |
|---|-------|----------|--------|
| 1 | All-full height arrays | `grids.py:301,318` | No sub-tile surface precision |
| 2 | Per-tile angle overwrites | `grids.py:302,319` | Discontinuous angle jumps |
| 3 | TOP_ONLY filter rejects ceiling during upward motion | `terrain.py:504` | Ceiling surface invisible at Q1->Q2 transition |
| 4 | Width array gives no precision with full tiles | `terrain.py:67-83` | Sensors snap to tile edges not arc |

The fix must address (1) and (2) in `build_loop()`. Issues (3) and (4) are
consequences of the geometry being wrong -- with proper per-pixel height arrays and
smoothly transitioning angles, the existing sensor system should be able to track the
surface continuously through all four quadrants.
