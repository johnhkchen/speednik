# Design — T-008-02: synthetic-tile-grid-builders

## Decision: height array computation strategy

### Option A: Pixel-level rasterization (like profile2stage)

Walk every pixel column, compute surface y, convert to tile-local height.
Exact match with how stages are built. Complex, couples to rasterizer logic.

### Option B: Tile-level analytical computation

Compute per-tile properties (angle, starting height) analytically.
Height array derived from slope geometry within each tile.
Simpler, self-contained, easier to verify.

### Decision: Option B — tile-level analytical

Rationale: Test helpers should be verifiable by inspection. Pixel-level
rasterization is unnecessarily precise for synthetic grids — we need
geometrically correct tiles, not pixel-perfect reproduction of the stage
pipeline. The analytical approach produces height arrays from basic trig
and is easier to reason about in tests.

**Exception**: The loop builder uses pixel-level circle math because
arc tiles can't be derived analytically per-tile without the circle
equation. This is simple enough to reimplement (5 lines of math).

## Decision: fill depth

### Option A: Fill to a fixed depth (e.g., +4 rows below surface)

Simple, predictable. But "bottom" varies per builder.

### Option B: Fill to a configurable grid bottom

Each builder takes `grid_height` or derives it from the geometry.

### Decision: Option A — fixed fill depth of 4 rows below surface

Rationale: Sensors extend at most 32 pixels (2 tiles). 4 rows of fill
is generous and avoids needing a grid boundary concept. The fill only
needs to prevent sensor fall-through, not model real terrain depth.

## Decision: loop builder approach

### Option A: Import _rasterize_loop internals from profile2stage

Direct reuse. But creates test dependency on code under test.

### Option B: Reimplement circle math inline

Self-contained. ~30 lines of circle geometry.

### Decision: Option B — reimplement inline

Rationale: The ticket explicitly says "test helpers shouldn't depend on
the code they're validating." The circle math is simple enough:
`dy = sqrt(r² - dx²)`, angle from `atan2`. The fill-below-loop logic
is also straightforward to reimplement.

## Decision: TileLookup wrapping

Reuse the `make_tile_lookup(tiles_dict)` pattern from test_terrain.py?
No — that helper is local to test_terrain.py. Define a local
`_wrap(tiles)` helper in grids.py. Trivial: `lambda tx, ty: tiles.get((tx, ty))`.

## Decision: self-tests

The ticket requires "each builder's output passes basic sanity checks."
Add a `test_grids.py` file with tests for each builder:
- Correct number of non-None tiles in the surface row
- Expected angle range
- No None tiles where surface should be
- Fill tiles exist below surface

## Height array computation formulas

### Flat
All columns = 16. Angle = 0. Solidity = FULL.

### Constant-angle slope
Given byte angle, convert to slope: `rise = tan(byte_to_rad(angle))`
For tile at row offset `row_offset` from surface start:
- Base height at column 0: `16 - row_offset * 16 * rise` (clamped 0–16)
- Height at column `col`: `base + col * rise` (clamped 0–16, rounded to int)
- When height exceeds 16 or drops to 0, tile is full or empty

### Ramp (linearly interpolated angle)
For tile index `i` in `[0, ramp_tiles)`:
- `t = (i + 0.5) / ramp_tiles` (center of tile in normalized space)
- `angle = lerp(start_angle, end_angle, t)` (in byte angles)
- Height array computed same as constant slope with that angle
- Cumulative row tracking: each ramp tile starts where the previous ended

### Loop (circle arc)
For each pixel column `px` in the loop circle:
- `dx = px - cx + 0.5`
- Bottom: `y = cy + sqrt(r² - dx²)`, upper: `y = cy - sqrt(r² - dx²)`
- Map to tile grid: `tx = px // 16`, `local_x = px % 16`
- Set `height_array[local_x] = 16` (full column, as profile2stage does)
- Bottom tiles: `solidity=FULL`, `tile_type=SURFACE_LOOP`
- Upper tiles: `solidity=TOP_ONLY`, `tile_type=SURFACE_LOOP`
- Interior tiles (between top_ty+1 and bottom_ty-1): left as None (hollow)
- Fill below: rows below lowest loop tile per column get flat full tiles

### Gap
Approach + landing are flat. Gap columns have no tiles at all.
Fill below approach and landing, not below gap.
