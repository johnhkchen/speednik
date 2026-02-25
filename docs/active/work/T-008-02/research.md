# Research — T-008-02: synthetic-tile-grid-builders

## Tile System Overview

### Core types (`speednik/terrain.py`)

- **`Tile`** dataclass (line 58): `height_array: list[int]`, `angle: int`, `solidity: int`, `tile_type: int = 0`
- **`TileLookup`** (line 50): `Callable[[int, int], Optional[Tile]]` — maps `(tx, ty)` to a Tile or None
- **Solidity constants**: `NOT_SOLID=0`, `TOP_ONLY=1`, `FULL=2`, `LRB_ONLY=3`
- **`TILE_SIZE = 16`** — each tile is 16×16 pixels
- **`SURFACE_LOOP = 5`** — tile_type for loop tiles (exempt from wall sensor blocking)

### Height array semantics

- 16 integers, one per pixel column (0=leftmost, 15=rightmost)
- Values 0–16: solid height from bottom of tile upward
- `[16]*16` = flat full tile, `[0]*16` = empty tile
- `[1,2,...,16]` = 45° upward slope left-to-right
- Surface y at column `col`: `ty * 16 + (16 - height_array[col])`

### Angle system

- Byte angles 0–255, one full revolution = 256 steps
- Conversion: `byte_angle = round(degrees * 256 / 360) % 256`
- Radians: `byte_angle_to_rad(angle) = angle * 2π / 256`
- Quadrants: 0 (floor, 0–32/224–255), 1 (right wall, 33–96), 2 (ceiling, 97–160), 3 (left wall, 161–223)
- Slope → angle: `round(-math.atan2(slope, 1.0) * 256 / (2*pi)) % 256`

### Sensor cast mechanics (`speednik/terrain.py` lines 133–209)

- Sensors cast down/up/left/right from a pixel position
- Extension: height=0 → check tile below; Regression: height=16 → check tile above
- Range: `MAX_SENSOR_RANGE = 32` pixels
- Fill below ground is critical: sensors that extend past empty tiles below surface will fail to detect ground

## Existing test helpers (`tests/test_terrain.py` lines 40–69)

- `degrees_to_byte(deg)` — degree-to-byte-angle conversion
- `make_tile_lookup(tiles: dict)` — wraps dict in TileLookup closure
- `flat_tile(angle=0, solidity=FULL)` — height `[16]*16`
- `empty_tile(solidity=FULL)` — height `[0]*16`
- `slope_45_tile(angle=0)` — height `[1,2,...,16]`
- `half_height_tile(angle=0)` — height `[8]*16`

These are single-tile helpers. No multi-tile grid builders exist yet.

## Loop generation reference (`tools/profile2stage.py` lines 627–706)

### Layout geometry

```
[entry_ramp (r_ramp px)] [loop_circle (2*radius px)] [exit_ramp (r_ramp px)]
```

- Circle center: `cx = loop_start + radius`, `cy = cursor_y - radius`
- Ground: `ground_y = cursor_y = cy + radius`

### Entry/exit ramps (quarter-circle arcs)

- Surface y: `cy + sqrt(r_ramp² - (px - arc_cx)²)`, clamped to ground_y
- Angle: finite difference `atan2(sy1 - sy0, 1)`
- Entry arc centered at `loop_start`; exit arc centered at `loop_end`

### Loop circle rasterization

- For each pixel column in `[loop_start, loop_end)`:
  - `dx = px - cx + 0.5`, `dy = sqrt(radius² - dx²)`
  - Bottom arc at `cy + dy`, top arc at `cy - dy`
  - Bottom angle: `round(-atan2(dx, dy) * 256 / 2π) % 256`
  - Top angle: `round(-atan2(-dx, -dy) * 256 / 2π) % 256`
- Loop tiles: `height_array` columns set to `TILE_SIZE` (full), `tile_type = SURFACE_LOOP`
- Upper arc tiles: `is_loop_upper = True` → exported as `solidity=TOP_ONLY`
- Lower arc tiles: `solidity=FULL`
- Interior is hollow (no tiles between top and bottom arcs)
- `_fill_below_loop()`: fills solid tiles below the lowest loop tile per column

### Solidity mapping (svg2stage.py line 1183)

- `SURFACE_LOOP` + `is_loop_upper=True` → `TOP_ONLY`
- `SURFACE_LOOP` + `is_loop_upper=False` → `FULL`
- This is how the collision.json export maps tile types to solidity

## Slope/ramp height computation

For a constant-angle slope, each pixel column's height within a tile:
- Rise per pixel = `tan(angle_in_radians)`
- At column `col` within a tile at position `start_col`: height from bottom = base + col * rise_per_pixel
- Must clamp to [0, 16]

For a linearly interpolated ramp across multiple tiles:
- Angle varies from `start_angle` to `end_angle`
- Each tile gets the interpolated angle at its center
- Height array computed from `tan(interpolated_angle)`

## File organization

- Target: `tests/grids.py` — new module, imported by test files
- No Pyxel imports allowed
- Depends only on `speednik.terrain` (Tile, TileLookup, FULL, TOP_ONLY, SURFACE_LOOP, TILE_SIZE)

## Key constraints

1. Height arrays must be geometrically correct — physics sensors read exact values
2. Ground fill below surface is mandatory to prevent sensor fall-through
3. Loop builder must distinguish upper/lower arc for solidity
4. Loop interior must be hollow (no tiles between arcs)
5. Test helpers should be self-contained — no imports from tools/ to avoid testing code with itself
6. All builders return `TileLookup` (the callable type alias)
