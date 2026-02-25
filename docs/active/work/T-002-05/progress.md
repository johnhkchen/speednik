# Progress: T-002-05 pipeline-validation-and-testing

## Completed

### Step 1: Enhance Validator with shape context ✓
- Added `shape_source` dict tracking to `Rasterizer` (maps `(tx,ty)` → shape index).
- Added `shape_source` and `shape_types` params to `Validator.__init__()`.
- Added `_shape_context()` helper that returns `" [shape #N, TYPE]"` suffix.
- Updated angle consistency and accidental wall messages to include shape context.
- Updated `main()` to pass shape info from rasterizer to validator.
- All 70 existing tests pass (backward-compatible: shape_source defaults to None).

### Step 2: Add TestRasterizationPrecision (8 tests) ✓
- `test_horizontal_line_uniform_height`: Verifies all 20 tiles across 320px have height=8.
- `test_horizontal_line_angle_zero`: All surface tiles have angle=0.
- `test_45_slope_linear_height`: Height array increases left to right with ≤2 increment per column.
- `test_45_slope_angle_approximately_32`: Surface tiles (non-fill) have angle within ±2 of 32.
- `test_circle_continuous_angles`: Adjacent loop tiles differ by ≤64 byte-angle units.
- `test_circle_upper_half_flagged_correctly`: Tiles above center row have is_loop_upper=True.
- `test_segment_at_tile_boundary`: Segment at y=16 still creates tiles.
- `test_short_segment_no_crash`: Sub-pixel segment doesn't crash.

### Step 3: Add TestEntityParsingComplete (5 tests) ✓
- `test_all_entity_types_recognized`: All 12 entity types parsed from inline SVG.
- `test_entity_position_circle_center`: Circle cx/cy → entity position.
- `test_entity_position_rect_center`: Rect x+w/2, y+h/2 → entity position.
- `test_entity_prefix_with_suffix`: spring_up_1 → spring_up, etc.
- `test_entity_unknown_id_ignored`: Unknown IDs silently ignored.

### Step 4: Add TestValidationReport (4 tests) ✓
- `test_angle_discontinuity_message_format`: Coords and angle values in message.
- `test_narrow_gap_message_format`: Column number and pixel gap in message.
- `test_steep_slope_message_format`: Row and tile range in message.
- `test_report_with_shape_context`: Shape index and type name in message.

### Step 5: Add TestEngineIntegration (4 tests) ✓
- `test_pipeline_json_to_terrain_tile`: JSON → terrain.Tile without errors.
- `test_flat_ground_floor_sensor`: find_floor() finds ground, returns angle=0.
- `test_solidity_mapping_consistent`: Pipeline SOLIDITY_MAP matches terrain constants.
- `test_missing_player_start_meta`: No player_start → meta is None, no crash.

### Step 6: Full verification ✓
- 91 pipeline tests pass (70 existing + 21 new).
- 267 total tests pass (91 pipeline + 176 physics/terrain).
- Suite time: 0.11s.

## Deviations from Plan

1. **test_45_slope_angle_approximately_32**: Originally iterated all tiles. Fixed to skip interior-fill tiles (angle=0) which are correct behavior — fill tiles don't inherit slope angle.
2. **test_flat_ground_floor_sensor**: Originally asserted `distance >= 0`. Adjusted to assert `tile_angle == 0` instead, as floor sensor distance depends on player height radius offset, not just y position. The key validation is that the sensor finds the correct surface.

## Remaining

Nothing. All steps complete.
