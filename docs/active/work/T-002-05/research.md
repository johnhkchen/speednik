# Research: T-002-05 pipeline-validation-and-testing

## Scope

Add comprehensive tests and validation tooling to the SVG-to-stage pipeline to catch geometry errors before they reach the engine. Reference: spec §4.4, ticket acceptance criteria.

## Existing Codebase

### Pipeline Tool: `tools/svg2stage.py` (1074 lines)

Four-layer architecture, stdlib-only (no speednik imports):

1. **SVGParser** (lines 442–596): Parses SVG XML → `(list[TerrainShape], list[Entity])`. Handles polygon/polyline, path (M/L/H/V/C/Q/Z), circle, ellipse, rect. Supports transform stacking (translate, scale, rotate, matrix). Stroke color → surface type mapping. Entity ID prefix matching (12 types, longest-first).

2. **Rasterizer** (lines 660–827): Terrain shapes → `TileGrid`. 1px-resolution segment walk. Computes byte angles via `-atan2(dy,dx) * 256/(2π) % 256`. Per-column height arrays (0–16). Interior fill below topmost surface tile per column. Loop handling: perimeter walk, `is_loop_upper` flagging.

3. **Validator** (lines 845–932): Three checks matching spec §4.4:
   - Angle consistency: neighbors differing >21 byte-angle units (~30°)
   - Impassable gaps: column gaps <18px between solid tiles
   - Accidental walls: >3 consecutive steep tiles without loop flag

4. **StageWriter** (lines 962–1030): Outputs tile_map.json, collision.json, entities.json, meta.json, validation_report.txt.

### Existing Tests: `tests/test_svg2stage.py` (781 lines, 70 tests)

| Class | Count | What it covers |
|-------|-------|----------------|
| TestPathParser | 11 | All SVG path commands, relative mode, close, implicit lineto |
| TestSVGParser | 16 | Stroke extraction, entity matching, viewbox, transforms, shapes |
| TestRasterizer | 11 | Flat/slope rasterization, angle computation, fill, top-only skip |
| TestLoopRasterization | 3 | Loop tiles, upper-half flagging, surface type |
| TestValidator | 10 | All three checks, wrap-around, top-only exemption, clean grid |
| TestStageWriter | 7 | All 5 output formats |
| TestTileGrid | 4 | Init, get/set, bounds |
| TestConstants | 2 | Color map, solidity map completeness |
| TestEndToEnd | 3 | Fixture parse, full pipeline, CLI subprocess |

### Test Fixture: `tests/fixtures/minimal_test.svg`

320×160 SVG with: flat ground polygon (#00AA00 at y=128), 45° slope polyline (#FF8800), player_start circle, 2 ring circles, 1 enemy_crab rect.

### Downstream Consumer: `speednik/terrain.py` (757 lines)

- `Tile` dataclass: `height_array: list[int]`, `angle: int`, `solidity: int`
- `width_array()`: Derived from height_array for wall detection
- Sensor system: `find_floor()`, `find_ceiling()`, `find_wall_push()`, `resolve_collision()`
- Solidity constants: `NOT_SOLID=0`, `TOP_ONLY=1`, `FULL=2`, `LRB_ONLY=3`

### Constants & Thresholds

Pipeline constants (svg2stage.py lines 24–96):
- `TILE_SIZE = 16`
- `ANGLE_CONSISTENCY_THRESHOLD = 21` (~30°)
- `MIN_GAP_PX = 18` (player width_radius × 2)
- `MAX_STEEP_RUN = 3`
- `STEEP_LOW = 32`, `STEEP_HIGH = 224`
- Surface types: EMPTY=0, SOLID=1, TOP_ONLY=2, SLOPE=3, HAZARD=4, LOOP=5

## Gap Analysis Against Acceptance Criteria

### AC1: Unit tests for rasterization
- **Horizontal line → same height, angle=0**: Partially covered. `test_horizontal_segment_flat` checks height=8 for a segment at y=8, but doesn't verify all tiles at same height. `test_angle_flat_rightward` checks angle. Need: a dedicated test that asserts all tiles across multiple columns have identical height values and angle=0.
- **45° slope → linearly increasing height, angle≈32**: Partially covered. `test_slope_segment_ramp` asserts height_array[0] < height_array[15] but doesn't verify linearity. `test_angle_45_ascending` checks angle=32. Need: test verifying height increments are roughly linear (±1) and angle is ~32 for all slope tiles.
- **Circle → continuous angles around perimeter, upper-half flagged**: `TestLoopRasterization` covers loop flag and surface type. But no test verifies angle continuity around the perimeter or that all upper-half tiles are correctly flagged.

### AC2: Unit tests for entity parsing
- **Type from id**: Covered (`test_match_entity_id_*`).
- **Position from center**: Covered for circles and rects individually.
- **All entity types in spec**: NOT covered. Only `ring`, `enemy_crab`, `player_start` tested. Missing: `liquid_trigger`, `enemy_buzzer`, `enemy_chopper`, `spring_right`, `spring_up`, `checkpoint`, `pipe_h`, `pipe_v`, `goal`.

### AC3: Validation tests
- **Angle discontinuity >30°**: Covered (`test_angle_consistency_flagged`).
- **Narrow gap <18px**: Covered (`test_impassable_gap_flagged`).
- **Steep slope >3 tiles**: Covered (`test_accidental_wall_flagged`).
- However: no test verifies the human-readable format with tile coordinates in messages.

### AC4: Integration test (SVG → pipeline → engine loads without errors)
- `test_full_pipeline` runs SVG → parse → rasterize → validate → write → read JSON.
- But NO test loads output into `terrain.Tile` objects. No test verifies sensor casts work on pipeline output. This is a significant gap.

### AC5: Validation report human-readable with SVG line references
- Reports include tile coordinates `(tx,ty)` but NOT SVG line numbers.
- Adding SVG line references would require tracking source element during parsing. `xml.etree.ElementTree` doesn't natively expose line numbers, but they can be recovered via a custom parser or by using `xml.sax`.
- Current format is human-readable (plain text, one issue per line).

## Open Concerns from T-002-01

1. Interior fill heuristic — incorrect for concave shapes with overhangs
2. Height array boundary precision — tile-aligned segments produce zero-height columns
3. No SVG arc (`A`) command support
4. No skewX/skewY transform support
5. Entity/terrain collision priority (underdocumented, untested)
6. No level.py consumer yet for end-to-end validation
7. Performance unverified for large levels

Items 1–5 are design flaws, not testing gaps. Item 6 is the key integration test gap. Item 7 is optional.

## Key Files

| File | Role | Lines |
|------|------|-------|
| `tools/svg2stage.py` | Pipeline tool (may need minor additions) | 1074 |
| `tests/test_svg2stage.py` | Test file (primary deliverable) | 781 |
| `tests/fixtures/minimal_test.svg` | Existing fixture | 17 |
| `speednik/terrain.py` | Integration target for engine-load test | 757 |
| `speednik/constants.py` | Player dimensions for gap validation | 75 |

## Constraints

- Pipeline is stdlib-only; tests can import speednik modules for integration tests.
- Existing tests use pytest with `sys.path.insert` for svg2stage imports.
- All 70 existing tests pass in 0.05s — test suite should remain fast.
- No new dependencies needed; just pytest (already in dev deps).
