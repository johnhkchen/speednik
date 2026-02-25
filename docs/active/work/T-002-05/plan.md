# Plan: T-002-05 pipeline-validation-and-testing

## Step 1: Enhance Validator with shape context

**What:** Add shape source tracking to Rasterizer and richer messages to Validator.

**Changes:**
- `Rasterizer`: Add `self.shape_source: dict[tuple[int,int], int]` initialized in `__init__`. In `_rasterize_line_segment` and `_rasterize_loop`, record `shape_source[(tx,ty)] = shape_index` where shape_index comes from enumerate in `rasterize()`.
- `Validator.__init__`: Accept `shape_source: dict[tuple[int,int], int] | None = None` and `shape_names: list[str] | None = None`.
- Validation messages: When shape_source is available, append `[shape #N, TYPE_NAME]` to each issue string.
- `main()`: Pass shape_source and names from rasterizer to validator.

**Verify:** All 70 existing tests still pass. Validation report output unchanged when shape_source is None.

## Step 2: Add TestRasterizationPrecision (AC1)

**Tests:**
1. `test_horizontal_line_uniform_height`: Horizontal line at y=120 across 320px → all 20 tiles have same height_array values, angle=0.
2. `test_horizontal_line_angle_zero`: Same setup, assert angle == 0 on all surface tiles.
3. `test_45_slope_linear_height`: 45° ascending line → height_array values increase roughly linearly (each col ±1 from expected).
4. `test_45_slope_angle_32`: Same slope → angle ≈ 32 (within ±2) on all slope tiles.
5. `test_circle_continuous_angles`: Circle r=48 → adjacent loop tiles differ by ≤ ANGLE_CONSISTENCY_THRESHOLD.
6. `test_circle_upper_half_flagged`: Circle → all tiles above center.y have is_loop_upper=True.
7. `test_segment_at_tile_boundary`: Segment at y=16 (exact boundary) → tile still created (documents boundary behavior).
8. `test_short_segment_no_crash`: Segment < 1px → no crash, no tiles created.

**Verify:** `pytest tests/test_svg2stage.py::TestRasterizationPrecision -v` — 8 pass.

## Step 3: Add TestEntityParsingComplete (AC2)

**Tests:**
1. `test_all_entity_types_recognized`: SVG with one `<circle>` per entity type → all 12 parsed.
2. `test_entity_position_circle_center`: Circle cx=100 cy=200 → entity at (100, 200).
3. `test_entity_position_rect_center`: Rect x=100 y=200 w=16 h=16 → entity at (108, 208).
4. `test_entity_prefix_with_suffix`: IDs like `ring_1`, `enemy_crab_3` → correct type, suffix stripped.
5. `test_entity_unknown_id_ignored`: Circle with `id="unknown_type"` → no entity, no crash.

**Verify:** `pytest tests/test_svg2stage.py::TestEntityParsingComplete -v` — 5 pass.

## Step 4: Add TestValidationReport (AC3 + AC5)

**Tests:**
1. `test_angle_discontinuity_message_format`: Grid with angle jump → message contains tile coords and angle values.
2. `test_narrow_gap_message_format`: Grid with 16px gap → message contains column number and gap size in pixels.
3. `test_steep_slope_message_format`: Grid with 5 steep tiles → message contains row and tile range.
4. `test_report_with_shape_context`: Validator with shape_source → messages include shape index and surface type name.

**Verify:** `pytest tests/test_svg2stage.py::TestValidationReport -v` — 4 pass.

## Step 5: Add TestEngineIntegration (AC4)

**Tests:**
1. `test_pipeline_json_to_terrain_tile`: Parse minimal SVG → pipeline → load tile_map.json → construct `terrain.Tile` instances → no errors.
2. `test_flat_ground_floor_sensor`: Load flat ground tiles → `find_floor()` returns found=True at correct distance.
3. `test_solidity_mapping_consistent`: For each surface type, verify `SOLIDITY_MAP[type]` in svg2stage matches `terrain` module's expectations.
4. `test_missing_player_start_meta`: SVG with no player_start → meta["player_start"] is None, no crash.

**Guard:** Wrap class with `@pytest.mark.skipif` if `speednik.terrain` import fails.

**Verify:** `pytest tests/test_svg2stage.py::TestEngineIntegration -v` — 4 pass.

## Step 6: Full test suite verification

**Run:** `uv run python -m pytest tests/test_svg2stage.py -v`
- Expected: 91 tests pass (70 existing + 21 new).
- No warnings, no deprecations.

**Run:** `uv run python -m pytest tests/ -v --tb=short`
- Full suite including physics/terrain tests all pass.
- No regressions from pipeline changes.

## Testing Strategy

- **Unit tests** (Steps 2–4): Test individual components with synthetic data. No file I/O except temp files.
- **Integration test** (Step 5): Tests cross-module boundary (pipeline → terrain). Uses temp directories for pipeline output.
- **Regression** (Step 6): All existing tests remain green.
- **No performance tests**: Not in acceptance criteria, suite stays fast (<1s).

## Commit Plan

1. After Step 1: "Enhance Validator with shape context in messages"
2. After Step 5: "Add 21 tests for rasterization, entities, validation, and engine integration (T-002-05)"
3. After Step 6: Only if fixups needed.
