# T-006-02 Research: profile2stage-core

## Objective

Map the codebase components relevant to building `tools/profile2stage.py` — a CLI that
reads `.profile.json` track definitions and emits the same four JSON files + validation
report that `tools/svg2stage.py` produces.

---

## Existing Stage Pipeline (svg2stage.py, 1113 lines)

### Data Classes

| Class | Purpose |
|-------|---------|
| `TileData` | Per-tile: `surface_type`, `height_array[16]`, `angle` (byte 0-255), `is_loop_upper` |
| `TileGrid` | 2D grid (cols × rows) of `TileData | None`. `set_tile()` / `get_tile()`. |
| `Entity` | `entity_type: str`, `x: float`, `y: float` |
| `Point` | Simple `x, y` pair |
| `TerrainShape` | SVG geometry container (not needed for profile2stage) |

### Constants

- `TILE_SIZE = 16`
- Surface types: `SURFACE_EMPTY(0)`, `SURFACE_SOLID(1)`, `SURFACE_TOP_ONLY(2)`,
  `SURFACE_SLOPE(3)`, `SURFACE_HAZARD(4)`, `SURFACE_LOOP(5)`
- Solidity flags: `NOT_SOLID(0)`, `TOP_ONLY(1)`, `FULL(2)`
- `SOLIDITY_MAP`: surface type → solidity flag
- Angle thresholds: `ANGLE_CONSISTENCY_THRESHOLD = 21`, `STEEP_LOW = 32`, `STEEP_HIGH = 224`
- Gap threshold: `MIN_GAP_PX = 18`

### Tile Height Array Semantics

16 integers (one per pixel column within a tile). Each value 0–16 = number of solid
pixels measured **from the bottom** of the tile. A flat ground surface at pixel y has
`height_array = [h]*16` where h = (tile_bottom_y - y). Fully solid interior tiles use
`[16]*16`.

### Byte Angle Convention

0 = flat rightward, 64 = wall (down), 128 = ceiling, 192 = wall (up), 224 = 45° upslope.
Computed as `round(-atan2(dy, dx) * 256 / (2π)) % 256` where dy is screen-coords (y-down).

For a ramp with rise < 0 (ascending, y decreases): dy < 0, dx > 0 → atan2 < 0 →
angle is in range ~224-255 depending on slope.

### Output Writer (StageWriter)

Writes to output directory:
- `tile_map.json`: `rows × cols` grid, each cell `null` or `{type, height_array, angle}`
- `collision.json`: `rows × cols` grid of solidity flags (0/1/2)
- `entities.json`: `[{type, x, y}, ...]`
- `meta.json`: `{width_px, height_px, width_tiles, height_tiles, player_start, checkpoints}`
- `validation_report.txt`: line-per-issue or "No issues found.\n"

### Validator

Operates on a `TileGrid`. Three checks:
1. **Angle consistency** — adjacent tile angle diff > 21 byte-units
2. **Impassable gaps** — column gaps 0 < gap < 18px between solid regions
3. **Accidental walls** — >3 consecutive steep tiles without loop flag

Constructor: `Validator(grid, shape_source=None, shape_types=None)`. The optional
shape tracking params are SVG-specific; profile2stage can pass `None` for both.

### Interior Fill Pattern (Rasterizer._fill_interior)

For each column in a shape's bounding region: find topmost surface tile, fill all tiles
below as fully solid (`height_array=[16]*16`, `angle=0`, same `surface_type`).
TOP_ONLY surfaces skip interior fill.

---

## Stage Loader (speednik/level.py, 119 lines)

`load_stage(stage_name)` reads the four JSON files and builds runtime `StageData`:
- `tile_map.json` + `collision.json` → `dict[(tx,ty), Tile]`
- `meta.json` → dimensions, player_start, checkpoints
- `entities.json` → raw entity list

The `Tile` runtime class (from `terrain.py`) stores `height_array`, `angle`, `solidity`.
The loader trusts that meta.json `player_start` is a dict with `x` and `y` keys (not null-safe — will crash if `player_start` is null). **profile2stage must produce `player_start: null` per ticket spec, which means generated stages won't be loadable by the game engine until entities are added (T-006-05).**

---

## Collision & Terrain (speednik/terrain.py, 776 lines)

Sensors cast from player position into the tile grid. Key: sensors expect `height_array`
measured from tile bottom. Floor sensors read `height_array[local_x]` where local_x is
`pixel_x % TILE_SIZE`. Wall sensors use `width_array` computed from height_array.

Flat ground tile with surface at pixel-y `ground_y` in tile row `ty`:
- `tile_bottom = (ty + 1) * TILE_SIZE`
- `height = tile_bottom - ground_y`
- `height_array = [height] * 16`

---

## Existing Stage Data (reference)

Three stages in `speednik/stages/`:
- `hillside`: 4800×720px (300×45 tiles), player_start (64, 610)
- `pipeworks`: 5600×1024px (350×64 tiles), player_start (200, 510)
- `skybridge`: 5200×896px (325×56 tiles)

---

## Testing Patterns (tests/test_svg2stage.py)

- Imports from `svg2stage` via `sys.path.insert(0, tools/)` pattern
- Uses `tempfile.mkstemp` / `tempdir` for output verification
- Class-based test grouping (e.g., `TestPathParser`, `TestRasterizer`, etc.)
- Direct assertions on `TileGrid` cell data, height_array values, etc.
- Validation tests construct grids manually and check Validator output

---

## Key Constraints for profile2stage

1. **Reuse `TileGrid`, `TileData`, `Validator`, `StageWriter`** from svg2stage — these are
   decoupled from SVG parsing and can be imported directly.
2. **Cursor state machine** is new: flat/ramp/gap segments advance (x, y, slope) sequentially.
3. **Ramp angle computation**: use same `round(-atan2(rise, len) * 256 / (2π)) % 256` formula.
4. **Interior fill**: replicate the column-by-column fill-below-surface pattern.
5. **Gap segments**: advance cursor without writing tiles (leave grid cells as None).
6. **Validation**: reuse `Validator(grid)` with no shape_source/shape_types.
7. **Slope warnings**: `abs(rise/len) > tan(30°) ≈ 0.577` → warning; `> 1.0` → error.
8. **Output**: `entities.json = []`, `meta.json player_start = null`.
