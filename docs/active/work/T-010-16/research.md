# Research — T-010-16: directional-terrain-raycast

## Scope

Implement `cast_terrain_ray()` in `speednik/terrain.py` that casts a ray from an arbitrary
origin at an arbitrary angle, returning `(distance, surface_angle_byte)`. This is the
foundation for the 7-ray observation fan described in the ticket.

---

## Existing Sensor Infrastructure

### File: `speednik/terrain.py` (784 lines)

The terrain module provides four axis-aligned sensor casts:

| Function              | Direction | Lines     |
|-----------------------|-----------|-----------|
| `_sensor_cast_down`   | +Y        | 133–208   |
| `_sensor_cast_up`     | −Y        | 211–326   |
| `_sensor_cast_right`  | +X        | 333–404   |
| `_sensor_cast_left`   | −X        | 407–471   |

Each cast:
1. Converts pixel position → tile grid + local offset
2. Reads `height_array[col]` (vertical) or `width_array()[row]` (horizontal)
3. Applies extension (check neighbor if current tile empty) and regression (check neighbor
   if current tile fully solid)
4. Returns `SensorResult(found, distance, tile_angle, tile_type)` with ±MAX_SENSOR_RANGE=32

These are **snap-based** sensors designed for collision resolution — they exploit the height
array to compute exact sub-tile distances. They only work along cardinal directions because
height_array encodes column-wise heights and width_array encodes row-wise widths.

### Key Data Structures

**TileLookup** (line 50): `Callable[[int, int], Optional[Tile]]` — maps grid coords to tile.

**Tile** (lines 58–83):
- `height_array: list[int]` — 16 values, 0–16. Index = column, value = pixels of solid from
  the bottom of the tile.
- `angle: int` — byte angle 0–255 representing surface orientation.
- `solidity: int` — NOT_SOLID(0), TOP_ONLY(1), FULL(2), LRB_ONLY(3).
- `tile_type: int` — 0=generic, 5=loop.

**TILE_SIZE** = 16 (line 43).

### Height/Width Array Geometry

In screen coordinates (Y increases downward):
- Tile top = `tile_y * 16`, tile bottom = `(tile_y + 1) * 16`
- Solid fills from bottom up: solid spans y ∈ `[(tile_y+1)*16 - h, (tile_y+1)*16)`
- Top of solid surface = `tile_y * 16 + (16 - h)`

The width_array is derived on-demand from height_array: for each row (0=bottom, 15=top),
count consecutive columns from the left that are solid at that row.

### SensorResult vs. Raycast Return

The existing `SensorResult` includes `found`, `distance`, `tile_angle`, `tile_type`. The
ticket's proposed return type is `tuple[float, int]` — `(distance, surface_angle_byte)`.
This is a simpler interface since the ray is for observation, not collision resolution.
No need for `found` — use `distance == max_range` as the "nothing found" sentinel.
No need for `tile_type` — observation doesn't distinguish loop surfaces.

---

## Observation Module

### File: `speednik/observation.py` (56 lines)

Current observation is 12-dimensional (OBS_DIM=12). The ticket and T-010-17 will extend
this to 26 dimensions by adding 7 rays × 2 values (distance + surface_angle).

The observation module imports from `simulation.py` (SimState) but not from `terrain.py`.
To use `cast_terrain_ray`, observation.py will need to import from terrain.py and access
`sim.tile_lookup`.

### Ray Fan Specification

7 rays at offsets from facing direction: `[-45, -30, -15, 0, 15, 30, 45]` degrees.
Convention: 0° = horizontal in facing direction, positive = downward, negative = upward.
Max range: 128.0 pixels. Normalization: distance/128.0, angle/255.0.

Ray origin: player center — `(x, y - half_height)` per ticket. The exact center depends
on standing vs. rolling (half_height is STANDING_HEIGHT_RADIUS or ROLLING_HEIGHT_RADIUS).

---

## Angle Conventions

The codebase uses byte angles (0–255 = 0–360°) extensively:
- `byte_angle_to_rad(angle)` in physics.py: `angle * 2π / 256`
- In the game's coordinate system: 0=right, 64=down-ish (90°), 128=left, 192=up-ish
- The tile `angle` field stores surface orientation in this scheme.

The ray angle convention in the ticket is different:
- 0° = horizontal right (or left if facing left)
- Positive = downward
- Negative = upward

This aligns with screen coordinates (Y-down). For right-facing, 0° ray → dx=+1, dy=0.
For 45° ray → dx=cos(45°), dy=sin(45°) — going down-right.

The `math` module uses standard trig where positive angle = counter-clockwise from +X axis,
but screen Y is inverted. So for screen coordinates: `dx = cos(θ)`, `dy = sin(θ)` when
θ is measured clockwise from +X (which matches the ticket's convention).

---

## Tile Occupancy Detection

For the step-based raycast, the key question at each step is: "Is this pixel inside solid
terrain?" The height_array gives us per-column solid information:

Given pixel `(px, py)`:
1. `tile_x = px // 16`, `tile_y = py // 16`
2. `col = px % 16`, `row = py % 16`
3. Look up tile at `(tile_x, tile_y)`
4. If tile exists and is solid: `height = tile.height_array[col]`
5. Pixel is solid if `row >= (16 - height)`, i.e., `height > (15 - row)` or equivalently
   `16 - height <= row` → the pixel is in the solid region.

More precisely: solid occupies rows `[16 - height, 16)` within the tile. A pixel at
local row `r` is solid iff `r >= 16 - height`, i.e., `height > 15 - r`.

Simplified: `height_array[col] > (TILE_SIZE - 1 - row)`.

---

## Performance Budget

The ticket specifies: 7 rays in < 1ms for 60fps. At max_range=128 and step=2:
- 128/2 = 64 steps per ray × 7 rays = 448 iterations
- Each iteration: integer division, dict lookup, comparison → ~microseconds in Python
- Total: well under 1ms even in pure Python

Step size of 2px is safe: smallest collision detail is 1px (height_array granularity is
1px per column), but for observation purposes, 2px resolution is sufficient. The ray
reports distance, not exact sub-pixel position.

A step size of 1px would be 896 iterations — still fast. Start with step=1 for accuracy,
optimize later if needed.

---

## Edge Cases

1. **Player in mid-air**: Rays pointing away from terrain may never hit → return (max_range, 0).
2. **Player inside solid**: First step immediately solid → return (0, angle_of_tile).
3. **Ray exits level bounds**: `tile_lookup` returns None for OOB → treat as empty.
4. **Negative coordinates**: `int(px) // 16` handles negatives correctly in Python (floor
   division), but `int(px)` truncates toward zero. Use `math.floor()` or `int()` carefully.
   Actually `int()` truncates toward zero; for negative coords this could be wrong. Use
   `int(math.floor(px))` or just `int(px) // 16` which in Python does floor division on ints.
5. **Zero-height tiles**: A tile with `height_array[col] == 0` at the ray's column is empty
   at every row → no hit in this tile.

---

## Constraints from Ticket

- No Pyxel imports (terrain.py already satisfies this).
- All existing tests must pass (`uv run pytest tests/ -x`).
- Function signature: `cast_terrain_ray(tile_lookup, origin_x, origin_y, angle_deg, max_range=128.0) -> tuple[float, int]`.
- Location: `speednik/terrain.py` (preferred over observation.py).

---

## Dependencies

T-010-13 (terrain sensor suite) is complete — all sensor functions are implemented and
tested. T-010-16 builds on the same `TileLookup` and `Tile` abstractions but does not
modify existing sensor code.

---

## Files That Will Be Touched

- `speednik/terrain.py` — add `cast_terrain_ray` function
- `tests/test_terrain.py` — add tests for the new function

No changes to observation.py in this ticket (that's T-010-17's job to wire up the rays).
