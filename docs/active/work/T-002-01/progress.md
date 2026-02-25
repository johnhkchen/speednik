# Progress: T-002-01 svg-to-stage-pipeline

## Completed Steps

### Step 1: Data classes and constants ✓
- Created `tools/svg2stage.py` with all data classes (Point, PathSegment, TerrainShape, Entity, TileData, TileGrid)
- Defined constants: TILE_SIZE, STROKE_COLOR_MAP, ENTITY_TYPES, SOLIDITY_MAP, surface type constants
- Created `tests/test_svg2stage.py` with TileGrid and constants tests

### Step 2: SVG path `d` attribute parser ✓
- Implemented `parse_path_d()` supporting M, L, H, V, C, Q, Z (absolute and relative)
- Handles implicit lineto after M, multiple coordinate pairs per command
- 11 tests covering all command types

### Step 3: SVG element parsing ✓
- Implemented SVGParser class with viewbox resolution, stroke color extraction, entity ID matching
- Supports polygon, polyline, path, circle, ellipse, rect elements
- Transform accumulation (translate, scale, rotate, matrix)
- Circle/ellipse disambiguated as terrain vs entity by stroke color vs id attribute
- 16 tests for parsing layer

### Step 4: Segment rasterization ✓
- Implemented Rasterizer with line segment walking at 1px resolution
- Height array computation from surface y-coordinate relative to tile bottom
- Angle computation using atan2 mapped to byte angles 0–255
- 11 tests for rasterization

### Step 5: Curve sampling and loop handling ✓
- Cubic and quadratic bezier sampling via de Casteljau evaluation
- Ellipse perimeter walking using Ramanujan approximation for step count
- Loop tiles flagged with is_loop_upper for quadrant mode switching
- 3 tests for loop rasterization

### Step 6: Interior fill ✓
- Fill below surface tiles as fully solid (height_array=[16]*16)
- Top-only platforms skip interior fill
- Tested as part of rasterizer tests

### Step 7: Validation ✓
- Angle consistency check (>21 byte-angle diff between neighbors)
- Impassable gap check (<18px between solid tiles)
- Accidental wall check (>3 consecutive steep tiles without loop flag)
- 10 tests for validation

### Step 8: Output writer ✓
- StageWriter produces tile_map.json, collision.json, entities.json, meta.json, validation_report.txt
- _build_meta extracts player_start and checkpoints from entity list
- 7 tests for writer

### Step 9: CLI entry point and end-to-end test ✓
- argparse CLI: `python tools/svg2stage.py input.svg output_dir/`
- Created tests/fixtures/minimal_test.svg with flat ground, slope, and entities
- 3 end-to-end tests including subprocess CLI invocation

### Step 10: Cleanup and verification ✓
- Deleted tools/.gitkeep
- Full test suite: 200 tests pass (70 new + 130 existing)

## Deviations from Plan

None. All steps completed as planned.
