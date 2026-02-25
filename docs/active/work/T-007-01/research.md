# T-007-01 Research: Loop Entry/Exit Ramps

## Relevant Files

### Primary Target
- **`tools/svg2stage.py`** (1113 lines) — The SVG-to-stage pipeline. Contains `_rasterize_loop()` (L745–796), the function that must be modified.

### Stage Data Consumers
- **`speednik/terrain.py`** (779 lines) — Tile collision system. Reads `height_array`, `angle`, `solidity`. Quadrant system rotates sensors based on angle. Wall sensor angle gate at L666–671 ignores tiles with `angle <= 48 or >= 208`.
- **`speednik/level.py`** — Stage loader; reads `tile_map.json`, `collision.json`, `entities.json`, `meta.json`.
- **`speednik/physics.py`** — `calculate_landing_speed()` uses byte angle for speed decomposition on landing.
- **`speednik/constants.py`** — `ANGLE_STEPS=256`, `WALL_ANGLE_THRESHOLD=48`.

### SVG Source
- **`stages/hillside_rush.svg`** — Loop at L233: `<circle cx="3600" cy="508" r="128">`. Ground at y=636. Approach ground x=3200–3472, exit ground x=3728–4000. Ground beneath loop x=3472–3728.

### Tests
- **`tests/test_svg2stage.py`** (~930 lines) — `TestLoopRasterization` (L430–470): verifies loop tile count, `is_loop_upper` flagging, `SURFACE_LOOP` type. `TestRasterizationPrecision` (L789–928): angle continuity, upper-half flagging.

## Current Loop Geometry (The Problem)

The `_ellipse_perimeter_segments()` function (L420–439) samples the circle at N evenly-spaced angles, producing line segments that approximate the perimeter. These are fed to `_rasterize_loop()`.

`_rasterize_loop()` walks each segment at 1px steps, creating tiles with:
- `surface_type = SURFACE_LOOP` (5)
- `height_array` computed from distance to tile bottom
- `angle` from segment direction via `_compute_segment_angle()`
- `is_loop_upper = True` if sample y < center y

The loop circle's bottom sits at `y = cy + r = 508 + 128 = 636` (ground level). The leftmost point is at `(cx - r, cy) = (3472, 508)`. The rightmost is at `(3728, 508)`.

**Gap:** There is no geometry connecting the flat ground (angle 0, at y=636) to the loop circle's leftmost tangent point (3472, 508) where the tangent is vertical (angle ~64). The player runs along flat ground, then suddenly encounters tiles with steep angles and no gradual transition. Wall sensors fire on these steep tiles and block the player.

## Angle System

Byte angles (0–255) map to directions:
- 0 = flat rightward (ground)
- 32 = ~45° ascending
- 64 = vertical (right wall)
- 128 = ceiling (leftward)
- 192 = vertical (left wall)
- 224 = ~45° descending

Quadrant boundaries in `terrain.py:get_quadrant()`:
- Q0 (floor): 0–32, 224–255
- Q1 (right wall): 33–96
- Q2 (ceiling): 97–160
- Q3 (left wall): 161–223

The wall sensor angle gate ignores tiles with `angle <= 48 or >= 208`, preventing ramp tiles from being treated as walls.

## Collision System Interaction

- **Regular solid tiles** (`SURFACE_SOLID=1`): `solidity=FULL`. Player walks normally.
- **Loop tiles** (`SURFACE_LOOP=5`): `solidity=FULL` (lower) or `TOP_ONLY` (upper, via `_write_collision`).
- **Ramp tiles** should be `SURFACE_SOLID` per ticket spec — standard ground, not loop geometry. This means they get `FULL` solidity and no special `is_loop_upper` handling.

The wall angle gate at `WALL_ANGLE_THRESHOLD=48` means ramp tiles with angles 0–48 will be ignored by wall sensors, which is correct for entry ramps. Tiles above ~48 byte-angle would need to be loop tiles (or the threshold adjusted) to avoid wall collisions.

## SVG Layout at Loop Section

```
x=3200          x=3472     cx=3600     x=3728          x=4000
   |  approach     |    loop circle     |     exit         |
   |  ground       |    r=128           |     ground       |
   |  y=636        |    cy=508          |     y=636        |
   |               |    bottom=636      |                  |
   |               |                    |                  |
   v               v                    v                  v
   ================*----....----*================
                  / loop circle  \
                 |    (hollow)    |
                  \              /
                   ----....----
```

Entry ramp fills gap from x=3472-r_ramp to x=3472, y from 636 (ground) up to 508 (tangent point).
Exit ramp fills gap from x=3728 to x=3728+r_ramp, y from 508 down to 636.

## Key Constraints

1. Ramp tiles must be `SURFACE_SOLID` (not `SURFACE_LOOP`) — the ticket is explicit about this.
2. Ramp tiles are generated BEFORE loop tiles so overlapping tiles at tangent points are overwritten by loop's own tiles.
3. Existing hollow-interior logic and ground fill must continue working unchanged.
4. Ramps only add new tiles outside the loop circle's x-range.
5. The `_fill_interior` method fills everything below surface tiles as solid — ramp tiles need this too.
6. Height arrays are per-column (16 values, one per pixel column in the tile).
7. Angles must transition smoothly from 0° at ground level to ~64° at tangent (entry) and ~192° to ~0° (exit).

## Existing Code Patterns

The `_rasterize_line_segment()` method (L697–743) provides the pattern: walk at 1px intervals, compute tx/ty/col, compute height from tile bottom, max with existing height. This is exactly what ramp rasterization needs, with the addition of analytical arc equations for height and angle rather than linear interpolation.

The `_fill_interior()` method (L798–831) fills columns below the topmost surface tile. If ramp tiles are `SURFACE_SOLID`, they'll be filled just like regular terrain — which is the desired behavior.
