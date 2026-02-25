# Structure — T-008-02: synthetic-tile-grid-builders

## New files

### `tests/grids.py`

Test utility module. Not a test file itself (no `Test` classes, no `test_` functions).

**Imports:**
```
import math
from speednik.terrain import Tile, TileLookup, FULL, TOP_ONLY, SURFACE_LOOP, TILE_SIZE
```

**Internal constants:**
```python
FILL_DEPTH = 4  # rows of solid fill below surface
```

**Internal helper:**
```python
_wrap(tiles: dict[tuple[int,int], Tile]) -> TileLookup
```
Returns `lambda tx, ty: tiles.get((tx, ty))`.

**Internal helper:**
```python
_fill_below(tiles: dict, tx: int, ground_row: int) -> None
```
Adds FILL_DEPTH rows of flat full tiles below `ground_row` at column `tx`.

**Internal helper:**
```python
_slope_height_array(angle_byte: int, col_offset: float = 0.0) -> list[int]
```
Computes a 16-element height array for a tile with the given byte angle.
`col_offset` shifts the starting height (for tiles mid-slope). Returns
heights clamped to [0, 16].

**Public builders (5 functions):**

1. `build_flat(width_tiles: int, ground_row: int) -> TileLookup`
2. `build_ramp(approach_tiles: int, ramp_tiles: int, start_angle: int, end_angle: int, ground_row: int) -> TileLookup`
3. `build_slope(approach_tiles: int, slope_tiles: int, angle: int, ground_row: int) -> TileLookup`
4. `build_gap(approach_tiles: int, gap_tiles: int, landing_tiles: int, ground_row: int) -> TileLookup`
5. `build_loop(approach_tiles: int, radius: int, ground_row: int, ramp_radius: int | None = None) -> TileLookup`

Each returns a `TileLookup` callable.

### `tests/test_grids.py`

Test file for the grid builders. One test class per builder.

**Classes:**
- `TestBuildFlat` — verifies surface tiles, fill below, tile count, angle=0
- `TestBuildRamp` — verifies approach is flat, ramp angles interpolated, height arrays vary
- `TestBuildSlope` — verifies constant angle, height arrays match slope geometry
- `TestBuildGap` — verifies approach, gap (None), landing, fill pattern
- `TestBuildLoop` — verifies approach, loop tile solidity, upper=TOP_ONLY, lower=FULL, hollow interior, fill below, tile_type=SURFACE_LOOP

## Modified files

None. This is a new module with no changes to existing code.

## Module boundaries

- `tests/grids.py` depends only on `speednik.terrain` (Tile, TileLookup, constants)
- `tests/test_grids.py` depends on `tests.grids` and `speednik.terrain` (for constants in assertions)
- No dependency on `tools/profile2stage.py` or `tools/svg2stage.py`
- No Pyxel imports anywhere

## Interface contracts

All builders return `TileLookup`:
- Returns `Tile` for coordinates within the constructed grid
- Returns `None` for coordinates outside the grid
- Grid coordinates are non-negative integers
- `ground_row` parameter: the tile row (y-index) where the surface sits
- Fill rows: `ground_row + 1` through `ground_row + FILL_DEPTH`
- Tile columns start at 0 for all builders

### build_flat
- Tiles at `(0..width-1, ground_row)`: flat full tiles
- Tiles at `(0..width-1, ground_row+1..+4)`: fill tiles

### build_ramp
- Approach at `(0..approach-1, ground_row)`: flat
- Ramp at `(approach..approach+ramp-1, ground_row)`: interpolated angles + height arrays
- Fill below all columns

### build_slope
- Approach at `(0..approach-1, ground_row)`: flat
- Slope at `(approach..approach+slope-1, ground_row)`: constant angle + slope heights
- Fill below all columns

### build_gap
- Approach at `(0..approach-1, ground_row)`: flat + fill
- Gap at `(approach..approach+gap-1, *)`: all None
- Landing at `(approach+gap..approach+gap+landing-1, ground_row)`: flat + fill

### build_loop
- Approach at `(0..approach-1, ground_row)`: flat + fill
- Loop section: computed from circle geometry, variable number of tile columns
- Optional ramp tiles before/after loop circle
- Exit flat tiles after loop + fill
- Returns TileLookup covering the full footprint
