# Plan: T-002-01 svg-to-stage-pipeline

## Step 1: Data classes and constants

Create `tools/svg2stage.py` with:
- All data classes: `Point`, `PathSegment`, `TerrainShape`, `Entity`, `TileData`, `TileGrid`
- Constants: `TILE_SIZE`, `STROKE_COLOR_MAP`, `ENTITY_TYPES`, `SOLIDITY_MAP`, surface type constants

Create `tests/test_svg2stage.py` with:
- Tests for `TileGrid` init, set/get
- Tests for `TileData` defaults
- Tests for constant mappings

Verify: `uv run pytest tests/test_svg2stage.py` passes.

## Step 2: SVG path `d` attribute parser

Implement `parse_path_d(d: str) -> list[PathSegment]`:
- Tokenizer: split `d` string into commands and coordinate pairs
- Handle absolute commands: M, L, H, V, C, Q, Z
- Handle relative commands: m, l, h, v, c, q, z
- Return list of `PathSegment` objects (lines and curves)

Tests:
- Parse simple M/L sequence → line segments with correct points
- Parse H/V shorthand → line segments
- Parse C (cubic bezier) → cubic segment with 4 points
- Parse Q (quadratic bezier) → quad segment with 3 points
- Parse Z → close path (line back to first M point)
- Parse relative commands (m, l, c) → correct absolute coordinates
- Parse real-world SVG path strings from Inkscape output

Verify: `uv run pytest tests/test_svg2stage.py -k "path_parser"` passes.

## Step 3: SVG element parsing

Implement `SVGParser`:
- `_resolve_viewbox()` — read SVG viewBox attribute, compute width/height
- `_get_stroke_color()` — extract stroke from `style` or `stroke` attribute, normalize hex
- `_match_entity_id()` — prefix-match element `id` against known entity types
- `_parse_polygon()`, `_parse_polyline()` — parse `points` attribute into line segments
- `_parse_path()` — use `parse_path_d` + apply transform
- `_parse_circle()`, `_parse_ellipse()` — entity or terrain based on stroke/id
- `_parse_rect()` — entity only
- `_accumulate_transform()`, `_apply_transform()` — affine transform math
- `parse()` — walk SVG tree, dispatch by tag, collect shapes and entities

Tests:
- Parse polygon points string → correct Point list
- Stroke color extraction from `style` and `stroke` attributes
- Entity ID matching: exact, prefixed (`ring_1`), compound (`enemy_crab_3`)
- ViewBox parsing
- Circle classified as entity (has entity id) vs terrain (has terrain stroke)
- Transform accumulation: translate, scale, nested group

Verify: `uv run pytest tests/test_svg2stage.py -k "svg_parser"` passes.

## Step 4: Segment rasterization

Implement `Rasterizer._rasterize_segment()`:
- Walk a line segment from p1 to p2
- For each tile the segment crosses, compute height_array column values
- Compute byte angle from segment slope
- Write to TileGrid

Implement `Rasterizer._compute_height_at_column()`:
- Given a surface y-coordinate and tile position, compute the height value (0–16) for one column

Implement `Rasterizer._compute_segment_angle()`:
- Convert segment direction to byte angle (0–255)

Tests:
- Horizontal segment at tile bottom → height_array = [16]*16, angle = 0
- Horizontal segment at tile midpoint → height_array = [8]*16
- 45° ascending segment → linear ramp height array, angle ≈ 32
- 45° descending segment → reverse ramp, angle ≈ 224
- Vertical segment → height values at boundary
- Segment crossing multiple tiles → each tile gets correct data
- Angle computation for cardinal directions: 0°, 90°, 180°, 270°

Verify: `uv run pytest tests/test_svg2stage.py -k "rasterize"` passes.

## Step 5: Curve sampling and loop handling

Implement `Rasterizer._sample_curve()`:
- Cubic bezier: evaluate at intervals along the curve using de Casteljau
- Return sampled points at ~16px arc-length intervals

Implement `Rasterizer._rasterize_loop()`:
- Walk ellipse perimeter at 16px arc-length intervals
- Compute tangent angle at each point → byte angle
- Flag upper-half tiles (y < center_y) as `is_loop_upper = True`
- Rasterize each perimeter segment

Tests:
- Cubic bezier sampling produces points at expected intervals
- Ellipse perimeter walk covers full 360°
- Tangent angles are continuous around the loop
- Upper-half tiles are flagged correctly
- Loop tiles have correct angles at cardinal points (top=128, bottom=0, right=64, left=192)

Verify: `uv run pytest tests/test_svg2stage.py -k "curve or loop"` passes.

## Step 6: Interior fill

Implement `Rasterizer._fill_interior()`:
- For each terrain shape, determine the interior region below the surface
- For each column, find the surface tile (topmost with height data)
- Fill all tiles below it (within the shape) as fully solid: height_array=[16]*16

Implement `Rasterizer.rasterize()` — orchestrate full pipeline:
- Process each shape: segments, curves, loops
- Fill interiors
- Return completed TileGrid

Tests:
- Single flat ground shape → surface tiles + solid tiles below
- Slope shape → surface with ramp heights, solid below
- Two terrain shapes don't interfere with each other
- Top-only platforms have no interior fill

Verify: `uv run pytest tests/test_svg2stage.py -k "fill or rasterize_full"` passes.

## Step 7: Validation

Implement `Validator`:
- `_check_angle_consistency()` — scan all tiles, check 4-neighbors, flag > 21 byte-angle diff
- `_check_impassable_gaps()` — scan columns, detect gaps < 18px between solid tiles
- `_check_accidental_walls()` — scan rows, detect > 3 consecutive steep tiles without loop flag
- `validate()` → return list of human-readable issue strings

Tests:
- Two adjacent tiles with 40° angle difference → flagged
- Two adjacent tiles with 20° difference → not flagged
- Wrap-around: angle 250 and angle 10 → diff is 16 → not flagged
- Gap of 16px between solid tiles → flagged
- Gap of 20px → not flagged
- Top-only gap → not flagged
- 4 consecutive steep tiles → flagged
- 4 consecutive steep loop tiles → not flagged
- 2 consecutive steep tiles → not flagged

Verify: `uv run pytest tests/test_svg2stage.py -k "valid"` passes.

## Step 8: Output writer

Implement `StageWriter`:
- `_write_tile_map()` — 2D array of {type, height_array, angle} objects; None tiles → null
- `_write_collision()` — 2D array of solidity ints (0–3)
- `_write_entities()` — flat list of {type, x, y}
- `_write_meta()` — {width_px, height_px, width_tiles, height_tiles, player_start, checkpoints}
- `_write_validation()` — plain text, one issue per line

Implement `build_meta()` — extract player_start from entities, collect checkpoints.

Tests:
- tile_map.json has correct structure and values
- collision.json values match SOLIDITY_MAP
- entities.json has correct fields
- meta.json has player_start extracted correctly
- validation_report.txt has one issue per line

Verify: `uv run pytest tests/test_svg2stage.py -k "writer"` passes.

## Step 9: CLI entry point and end-to-end test

Implement `main()`:
- argparse: `input_svg` (positional), `output_dir` (positional)
- Wire: parse → rasterize → validate → write
- Print summary to stdout: tile count, entity count, issue count

Create `tests/fixtures/minimal_test.svg`:
- ViewBox: 320x160 (20×10 tiles)
- Flat ground strip: polygon with #00AA00 stroke at y=128 (bottom 2 tile rows)
- 45° slope: polyline with #FF8800 stroke, 3 tiles ascending
- Entities: player_start circle, 2 ring circles, 1 enemy_crab rect

Tests:
- End-to-end: parse minimal_test.svg → write to temp dir → read back JSON → verify:
  - Tile map dimensions match viewBox
  - Ground tiles have height_array=[16]*16
  - Slope tiles have ramped height arrays
  - Entities list contains all 4 entities with correct types and positions
  - Meta has correct player_start
  - Validation report exists (may be empty)
- CLI invocation via subprocess: `python tools/svg2stage.py tests/fixtures/minimal_test.svg /tmp/test_output/` → exit code 0, files exist

Verify: `uv run pytest tests/test_svg2stage.py` — all tests pass.

## Step 10: Delete .gitkeep, final verification

- Delete `tools/.gitkeep`
- Run full test suite: `uv run pytest` — all 98 existing + new tests pass
- Run the CLI on the test fixture and inspect output

## Testing Strategy

- **Unit tests:** Each layer tested independently with synthetic inputs
- **Integration test:** End-to-end SVG → JSON with a minimal fixture
- **CLI test:** Subprocess invocation to verify argparse and file I/O
- **No mocking:** Tests create real TileGrids, parse real (inline) SVG strings
- **Fixtures:** Minimal SVGs defined as string constants in the test file + one .svg file for CLI test
