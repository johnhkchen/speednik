# Structure: T-002-01 svg-to-stage-pipeline

## Files Created

### `tools/svg2stage.py` (main tool — ~600 lines)

Single self-contained file. No imports from the `speednik` package (standalone build tool). Dependencies: stdlib only (`xml.etree.ElementTree`, `math`, `json`, `sys`, `os`, `re`, `argparse`).

#### Module Organization

```
# --- Constants & Color Mapping ---
TILE_SIZE = 16
STROKE_COLOR_MAP: dict mapping hex colors → surface types
ENTITY_TYPES: set of known entity type strings
SOLIDITY_MAP: dict mapping surface type → solidity value

# --- SVG Parsing Layer ---
class SVGParser:
    """Parses SVG document into intermediate terrain and entity data."""

    def __init__(self, svg_path: str)
    def parse(self) -> tuple[list[TerrainShape], list[Entity]]

    # Private:
    _parse_element(element, parent_transform) → dispatches by tag
    _parse_polygon(element, transform) → TerrainShape
    _parse_polyline(element, transform) → TerrainShape
    _parse_path(element, transform) → TerrainShape
    _parse_circle(element, transform) → TerrainShape or Entity
    _parse_ellipse(element, transform) → TerrainShape or Entity
    _parse_rect(element, transform) → Entity
    _get_stroke_color(element) → str or None
    _match_entity_id(element) → str or None
    _resolve_viewbox() → (width, height)
    _accumulate_transform(parent, local) → combined 3x3 matrix
    _apply_transform(point, matrix) → transformed point

# --- SVG Path Parser ---
def parse_path_d(d: str) -> list[PathSegment]:
    """Parse SVG path 'd' attribute into segment list."""
    # Handles: M, L, H, V, C, Q, Z (absolute)
    # Handles: m, l, h, v, c, q, z (relative)
    # Returns list of PathSegment(type, points)

# --- Data Classes ---
@dataclass
class Point:
    x: float
    y: float

@dataclass
class PathSegment:
    kind: str            # 'line', 'cubic', 'quad'
    points: list[Point]  # control points

@dataclass
class TerrainShape:
    segments: list[PathSegment]  # edge segments
    surface_type: int            # 1=solid, 2=top-only, 3=slope, 4=hazard
    is_loop: bool                # True for circle/ellipse terrain
    center: Point | None         # center for loops

@dataclass
class Entity:
    entity_type: str     # 'ring', 'enemy_crab', etc.
    x: float
    y: float

# --- Rasterization Layer ---
class Rasterizer:
    """Converts terrain shapes into tile grid."""

    def __init__(self, width_px: int, height_px: int)
    def rasterize(self, shapes: list[TerrainShape]) -> TileGrid

    # Private:
    _rasterize_shape(shape: TerrainShape)
    _rasterize_segment(p1, p2, surface_type) → updates tile grid
    _rasterize_loop(shape: TerrainShape) → walk ellipse perimeter
    _sample_curve(segment, interval=16) → list[Point]
    _compute_height_at_column(surface_y, tile_y, col) → int (0–16)
    _compute_segment_angle(p1, p2) → int (byte angle 0–255)
    _fill_interior(shape: TerrainShape) → mark below-surface tiles as solid

# --- Tile Grid ---
class TileGrid:
    """2D grid of tile data."""

    def __init__(self, cols: int, rows: int)
    tiles: list[list[TileData | None]]   # [row][col], None = empty

    def set_tile(self, tx, ty, tile_data)
    def get_tile(self, tx, ty) → TileData | None

@dataclass
class TileData:
    surface_type: int             # 1–5
    height_array: list[int]       # 16 values, 0–16
    angle: int                    # byte angle 0–255
    is_loop_upper: bool           # flag for quadrant switching

# --- Validation Layer ---
class Validator:
    """Runs validation checks on rasterized tile grid."""

    def __init__(self, grid: TileGrid)
    def validate(self) -> list[str]

    # Private:
    _check_angle_consistency() → list[str]
    _check_impassable_gaps() → list[str]
    _check_accidental_walls() → list[str]

# --- Output Layer ---
class StageWriter:
    """Writes pipeline output files."""

    def __init__(self, output_dir: str)
    def write(self, grid: TileGrid, entities: list[Entity],
              meta: dict, issues: list[str])

    # Private:
    _write_tile_map(grid) → tile_map.json
    _write_collision(grid) → collision.json
    _write_entities(entities) → entities.json
    _write_meta(meta) → meta.json
    _write_validation(issues) → validation_report.txt

# --- CLI Entry Point ---
def main():
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args()

    svg = SVGParser(args.input_svg)
    shapes, entities = svg.parse()

    rasterizer = Rasterizer(svg.width, svg.height)
    grid = rasterizer.rasterize(shapes)

    validator = Validator(grid)
    issues = validator.validate()

    meta = build_meta(svg, entities, grid)

    writer = StageWriter(args.output_dir)
    writer.write(grid, entities, meta, issues)

if __name__ == '__main__':
    main()
```

### `tests/test_svg2stage.py` (~300 lines)

Test file covering all pipeline layers:

```
# --- Fixtures ---
MINIMAL_SVG: str constant — flat ground + slope + entities
LOOP_SVG: str constant — circle terrain element

# --- Test Classes ---
class TestPathParser:
    # parse M, L commands
    # parse C (cubic bezier) commands
    # parse relative commands (m, l)
    # parse Z close

class TestSVGParser:
    # parse polygon points
    # parse polyline points
    # stroke color mapping
    # entity id matching (prefix with underscore)
    # entity id matching (exact)
    # viewbox resolution
    # circle as entity vs terrain (by id vs stroke color)
    # transform accumulation

class TestRasterizer:
    # flat horizontal segment → all-16 height arrays
    # 45° slope → linear ramp height arrays
    # segment angle computation
    # curve sampling at 16px intervals
    # loop perimeter walk
    # interior fill below surface

class TestValidator:
    # angle inconsistency detection
    # gap detection
    # accidental wall detection
    # clean grid passes all checks

class TestStageWriter:
    # tile_map.json format
    # collision.json format
    # entities.json format
    # meta.json format

class TestEndToEnd:
    # minimal SVG → full output files
    # validates output matches expected tile data
```

### `tests/fixtures/minimal_test.svg` (~30 lines)

Minimal SVG for end-to-end testing: flat ground strip, one 45° slope, player_start, two rings, one enemy.

## Files Modified

### `tools/.gitkeep`
Deleted — replaced by actual content.

### `pyproject.toml`
No changes needed. The tool uses only stdlib. pytest is already a dev dependency.

## Module Boundaries

```
svg2stage.py (standalone — no speednik imports)
    │
    ├── SVGParser → reads SVG, produces TerrainShape + Entity lists
    │
    ├── Rasterizer → converts shapes to TileGrid
    │
    ├── Validator → checks grid for issues
    │
    └── StageWriter → outputs JSON files
```

Data flows in one direction: SVG → parse → rasterize → validate → write.

No circular dependencies. Each layer depends only on shared data classes (`Point`, `TerrainShape`, `Entity`, `TileData`, `TileGrid`).

## Interface with Engine

The output JSON must be loadable by the future `level.py` module (not yet written). The contract:

- `tile_map.json` tiles have fields that map 1:1 to `terrain.Tile`: `height_array` → `Tile.height_array`, `angle` → `Tile.angle`
- `collision.json` provides `solidity` values matching terrain.py constants (0–3)
- Entity types in `entities.json` are string names matching future `enemies.py` / `objects.py` types
- `meta.json` provides `width_tiles`, `height_tiles`, `player_start` {x, y}, `checkpoints` [{x, y}]

## Constants Alignment

The tool defines its own `TILE_SIZE = 16` rather than importing from `speednik.terrain`. This avoids a package dependency and keeps the tool standalone. Both values must stay in sync — any future change to tile size requires updating both locations. This is acceptable because tile size is a fundamental constant unlikely to change.

## Transform Handling

SVG transforms are represented as 3×3 affine matrices. `_accumulate_transform` multiplies parent × child. `_apply_transform` applies the matrix to a point. Supported transforms: `translate(tx, ty)`, `scale(sx, sy)`, `rotate(angle)`, `matrix(a,b,c,d,e,f)`. This covers the transforms Inkscape and Illustrator produce.

## Ordering Constraints

1. Path parser must be implemented before SVGParser (SVGParser calls it for `<path>` elements)
2. Data classes must be defined before any class that uses them
3. Rasterizer before Validator (validator operates on TileGrid)
4. All layers before CLI entry point
