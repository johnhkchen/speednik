# Research: T-002-01 svg-to-stage-pipeline

## Scope

Build `tools/svg2stage.py` — a standalone CLI that converts designer-drawn SVG files into the tile map, collision data, and entity placement the engine loads. Reference: specification §4.

## Existing Codebase

### Tile Data Structure (terrain.py)

The engine's `Tile` dataclass defines the target format:
```python
@dataclass
class Tile:
    height_array: list[int]   # 16 values, 0–16 per column
    angle: int                # byte angle 0–255
    solidity: int             # NOT_SOLID=0, TOP_ONLY=1, FULL=2, LRB_ONLY=3
```

Key properties:
- `height_array[col]` = solid pixels from bottom in column `col` (0=empty, 16=full)
- `width_array()` is computed on-the-fly from height_array (not stored)
- Angle 255 is a sentinel meaning "use nearest 90° cardinal" — currently not handled specially in terrain.py (noted in T-001-03 review)
- TILE_SIZE = 16 (from terrain.py constants)
- MAX_SENSOR_RANGE = 32 (one tile + one adjacent)

### Solidity Constants (terrain.py)

```python
NOT_SOLID = 0   # terrain stroke color → no tile needed (air)
TOP_ONLY  = 1   # #0000FF stroke → jump-through platform
FULL      = 2   # #00AA00 stroke → standard solid ground
LRB_ONLY  = 3   # Not mapped from any SVG color in the spec
```

### Physics Integration Points

`TileLookup = Callable[[int, int], Optional[Tile]]` — the interface the level loader must provide. Takes tile-grid coords `(tx, ty)`, returns `Tile` or `None`.

`PhysicsState` uses:
- `angle` (byte 0–255) — snapped from tile data on landing/floor contact
- `on_ground`, `y_vel` — determine top-only collision behavior
- `calculate_landing_speed(state)` — depends on tile angle at landing point

### Existing File Layout

- `tools/` exists with `.gitkeep` only — `svg2stage.py` goes here
- `speednik/stages/` has empty `__init__.py` — will eventually hold Python stage data modules
- No `level.py` yet — that loads pipeline output at runtime; not part of this ticket

### Test Infrastructure

- pytest via `uv run pytest`
- 98 existing tests (37 physics, 61 terrain)
- Tests use dict-based `TileLookup` — `{(tx, ty): Tile(...)}`
- Helper: `flat_tile()`, `slope_45_tile()`, `half_height_tile()`

### Dependency Constraints

- `pyproject.toml` has only `pyxel` as runtime dep, `pytest` as dev dep
- SVG parsing will need a library or stdlib `xml.etree.ElementTree`
- No numpy/scipy — keep it lean; stdlib math is sufficient for geometry

## SVG Format Requirements (from spec §4)

### Terrain Elements

| SVG element | Stroke color | Surface type | Solidity |
|------------|-------------|-------------|---------|
| Closed polygon/polyline | `#00AA00` | Solid ground | FULL (2) |
| Closed polygon/polyline | `#0000FF` | Top-only | TOP_ONLY (1) |
| Closed polygon/polyline | `#FF8800` | Slope | FULL (2) |
| Closed polygon/polyline | `#FF0000` | Hazard | FULL (2) |
| Circle/ellipse | terrain color | Loop | FULL (2) |

Fill is ignored. Only stroke color and geometry matter.

### Entity Elements

`<circle>` or `<rect>` with `id` attribute:
- `player_start`, `ring`, `enemy_crab`, `enemy_buzzer`, `enemy_chopper`
- `spring_up`, `spring_right`, `goal`, `checkpoint`
- `pipe_h`, `pipe_v`, `liquid_trigger`

Position = element center point.

### ViewBox

1:1 mapping to world pixels. ViewBox `width × height` = world pixel dimensions.

## Output Format (from spec §4.2)

Five files per stage:
1. `tile_map.json` — 2D array of `{type, height_array, angle}`
2. `collision.json` — solidity flags per tile (parallel 2D array)
3. `entities.json` — flat array of `{type, x, y}`
4. `meta.json` — stage width/height in pixels/tiles, player_start, checkpoints
5. `validation_report.txt` — all flagged issues

## Rasterization Requirements (from spec §4.3)

### Straight Segments
- Rasterize into tile grid
- Angle = segment slope in byte angle (0–255)
- Height arrays from geometry occupancy per column

### Curved Paths
- Sample at 16px intervals along the curve
- Tangent angle at each sample → tile angle
- Each sample maps to its containing tile

### Loops (Ellipses)
- Walk ellipse perimeter at 16px intervals
- Assign continuous angle values
- Flag upper-half tiles for quadrant mode switching

### Height Array Computation
- For each tile column, determine how much SVG geometry occupies it
- 45° diagonal → linearly increasing array [0,1,2,...,15,16]
- Flat ground → all-16 array

## Validation Rules (from spec §4.4)

1. **Angle inconsistency:** Adjacent tiles differ by > ~30° in byte angle (~21 byte-angle units)
2. **Impassable gaps:** Terrain gaps < 18px that aren't top-only
3. **Accidental walls:** Slope > 45° for > 3 consecutive tiles without loop flag

## SVG Parsing Challenges

### Path Data (`d` attribute)
SVG `<path>` elements use a compact notation: M (moveto), L (lineto), C (cubic bezier), Q (quadratic bezier), Z (close), A (arc). Need to parse this reliably.

### Transforms
SVG elements can have `transform` attributes (translate, rotate, scale, matrix). These must be resolved to get final world coordinates.

### Coordinate System
SVG y-axis points down (same as screen/Pyxel), so no y-flip needed for position mapping. But angles need care — SVG arcs use different conventions than the engine's byte angles.

### Polygon/Polyline vs Path
Terrain could be `<polygon>`, `<polyline>`, or `<path>`. All need parsing. Polygons auto-close; polylines may or may not be closed.

### Nested Groups
SVG `<g>` elements group children with shared transforms. Must traverse the tree applying accumulated transforms.

## Key Questions

1. **SVG parsing library:** stdlib `xml.etree.ElementTree` handles XML. Path `d` attribute parsing requires custom code or a library. `svgpathtools` is a well-known option but adds a dependency.
2. **Stroke color matching:** Need hex color normalization (case-insensitive, with/without `#`, short-form expansion).
3. **Entity `id` disambiguation:** SVG allows `id` prefixes (e.g., `ring_1`, `ring_2`). Need a matching strategy — prefix match or exact match with numbering convention.
4. **Loop detection:** How to distinguish a terrain ellipse (loop) from an entity circle? Answer: terrain elements have terrain stroke colors; entity elements have `id` attributes.
5. **Type field in tile_map.json:** The spec shows `"type": 1` but doesn't define the mapping. Likely: 0=empty, 1=solid, 2=top-only, 3=slope, 4=hazard. Or it could be the solidity value. Need to decide.

## Constraints and Assumptions

- No external SVG libraries — use stdlib XML parsing + custom path parsing
- The tool must work standalone: `python tools/svg2stage.py input.svg output_dir/`
- No Pyxel dependency — this is a build tool, not runtime code
- Output JSON must be loadable by the future `level.py` module
- Keep the tool simple enough that SVG creation in Inkscape/Illustrator is practical
- Entity IDs use prefix matching to allow `ring_1`, `ring_2`, etc.
