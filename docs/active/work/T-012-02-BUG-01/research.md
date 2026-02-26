# Research — T-012-02-BUG-01: hillside-wall-at-x601

## Problem Summary

Walker, Cautious, and Wall Hugger strategies all stall at x≈601 in Hillside Rush.
The player hits a wall-angle tile and bounces upward instead of walking smoothly
through what is geometrically a gentle slope transition.

## Root Cause: Tile Data

Tile at grid position **(37, 38)** — pixel range x=[592, 608), y=[608, 624) —
carries `angle=64` (byte angle for 90°, right-wall quadrant) while its
height_array and neighboring tiles describe a gentle floor ramp.

### Surrounding tile survey (row 38)

| tx  | angle | height_array (16 values)                                | role        |
|-----|-------|---------------------------------------------------------|-------------|
| 35  |   0   | [4]*16                                                  | flat floor  |
| 36  |   0   | [4]*16                                                  | flat floor  |
| **37** | **64** | [4,4,4,4,4,4,4,4,4,5,5,5,5,5,5,5]                | **BUG**     |
| 38  |   2   | [5]*16                                                  | gentle ramp |
| 39  |   2   | [5,5,6,6,6,6,6,6,6,6,6,6,6,6,6,6]                    | gentle ramp |
| 40  |   5   | [6,6,6,6,6,6,6,6,6,6,6,7,7,7,7,7]                    | mild slope  |
| 41  |   5   | [7,7,7,8,8,8,8,8,8,8,8,9,9,9,9,9]                    | mild slope  |

The height array for tile 37 rises from 4→5 across 16 columns — a slope of
1/16 pixels per column. The correct angle for this geometry is approximately
**2** (matching tile 38 immediately to the right), not 64.

## Physics Impact Chain

1. Player walks right at ground_speed ≈ 6.0, on_ground=True, angle=0.
2. Floor sensor (A or B) reads tile (37, 38). `_snap_to_floor()` sets
   `state.angle = 64`.
3. `get_quadrant(64)` returns **1** (right-wall mode, range 33–96).
4. Two-pass logic in `resolve_collision()` fires: new quadrant ≠ old quadrant →
   second floor sensor pass casts **RIGHT** instead of DOWN.
5. The second pass's RIGHT-cast sensor finds a wall surface, snaps `state.x`.
6. `calculate_landing_speed()` decomposes ground_speed into x_vel/y_vel using
   the 64-angle → x_vel drops to 0.0, y_vel becomes -5.875 (upward launch).
7. Player arcs upward and lands ~13px ahead, then oscillates between angle=64
   and angle=0 tiles, never making sustained forward progress.

## Data Pipeline Context

Tile data originates from `speednik/stages/hillside/tile_map.json`, loaded by
`speednik/level.py:_build_tiles()` (line 97). The JSON is produced by an
offline pipeline that extracts collision data from Pyxel tilemap resources.

The angle value is stored per-cell in `tile_map.json[row][col]["angle"]`.
Solidity comes from a separate `collision.json[row][col]` integer. The loader
directly trusts these values — no runtime validation or correction occurs.

### Key files

| File                                              | Role                                 |
|---------------------------------------------------|--------------------------------------|
| `speednik/stages/hillside/tile_map.json`          | Raw tile data (height arrays, angles)|
| `speednik/stages/hillside/collision.json`         | Solidity values per cell             |
| `speednik/level.py`                               | Loader: JSON → Tile dict → TileLookup|
| `speednik/terrain.py`                             | Collision resolution, sensor casts   |
| `speednik/physics.py`                             | PhysicsState, calculate_landing_speed|
| `speednik/constants.py`                           | WALL_ANGLE_THRESHOLD (48)            |

## Relevant Constants

- `WALL_ANGLE_THRESHOLD = 48`: wall sensor angle gate boundary
- `ANGLE_STEPS = 256`: byte-angle full circle
- Quadrant boundaries: 0 (0–32, 224–255), 1 (33–96), 2 (97–160), 3 (161–223)

## Correctness Check

The height array `[4,4,4,4,4,4,4,4,4,5,5,5,5,5,5,5]` has a rise of 1 pixel
over 16 columns. The slope angle in radians is `atan(1/16) ≈ 0.0625 rad`,
which converts to byte angle: `0.0625 / (2π/256) ≈ 2.55` → rounds to **2** or
**3**. The adjacent tiles (38, 39) use angle=2, confirming the correct value.

## Scope

This is a single-tile data fix in `tile_map.json`. No code changes to the
physics engine, terrain system, or loader are required. The engine is behaving
correctly given the data — the data itself is wrong.
