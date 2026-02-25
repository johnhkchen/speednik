# Review: T-002-05 pipeline-validation-and-testing

## Summary of Changes

### Files Modified
- **`tools/svg2stage.py`** (~20 lines added): Rasterizer tracks shape source per tile. Validator accepts optional shape metadata and includes shape index/type in validation messages. Backward-compatible — callers without shape info get identical output.
- **`tests/test_svg2stage.py`** (~300 lines added): 21 new tests across 4 test classes.

### Files Created
- **`docs/active/work/T-002-05/`**: research.md, design.md, structure.md, plan.md, progress.md, review.md

### Files Unchanged
- All `speednik/*.py` source files (read-only dependency for integration tests)
- `tests/fixtures/minimal_test.svg` (reused by integration tests)
- `pyproject.toml` (no new dependencies)

## Test Coverage

### Before: 70 tests (T-002-01 baseline)
### After: 91 tests (+21 new)
### Full suite: 267 tests (91 pipeline + 176 physics/terrain), all passing in 0.11s

| New Class | Tests | Acceptance Criteria |
|-----------|-------|---------------------|
| TestRasterizationPrecision | 8 | AC1: Horizontal line → uniform height/angle=0. 45° slope → linear height ramp, angle≈32. Circle → continuous angles, upper-half flagged. Boundary/edge cases. |
| TestEntityParsingComplete | 5 | AC2: All 12 entity types recognized. Circle/rect center positions. Prefix matching with suffixes. Unknown IDs rejected. |
| TestValidationReport | 4 | AC3+AC5: Message format includes tile coordinates, angle values, pixel gaps, tile ranges. Shape context (index + type name) when available. |
| TestEngineIntegration | 4 | AC4: Pipeline JSON → terrain.Tile construction. Floor sensor finds ground. Solidity mapping consistent. Missing player_start handled. |

## Acceptance Criteria Coverage

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Unit tests: horizontal line → same height, angle=0 | ✓ | `test_horizontal_line_uniform_height`, `test_horizontal_line_angle_zero` |
| Unit tests: 45° slope → linear height, angle≈32 | ✓ | `test_45_slope_linear_height`, `test_45_slope_angle_approximately_32` |
| Unit tests: circle → continuous angles, upper-half flagged | ✓ | `test_circle_continuous_angles`, `test_circle_upper_half_flagged_correctly` |
| Unit tests: entity type from id | ✓ | `test_all_entity_types_recognized` |
| Unit tests: entity position from center | ✓ | `test_entity_position_circle_center`, `test_entity_position_rect_center` |
| Unit tests: all entity types in spec | ✓ | `test_all_entity_types_recognized` (all 12 types) |
| Validation: angle discontinuity >30° flagged | ✓ | `test_angle_discontinuity_message_format` (existing `test_angle_consistency_flagged` also covers) |
| Validation: narrow gap <18px flagged | ✓ | `test_narrow_gap_message_format` |
| Validation: steep slope >3 tiles flagged | ✓ | `test_steep_slope_message_format` |
| Integration: SVG → pipeline → engine loads | ✓ | `test_pipeline_json_to_terrain_tile`, `test_flat_ground_floor_sensor` |
| Validation report human-readable with references | ✓ | Shape context in messages: `[shape #N, TYPE]`. Tile coordinates in all messages. |

## Pipeline Changes

The Validator enhancement is minimal and backward-compatible:

1. `Rasterizer.shape_source`: New dict populated during rasterization mapping `(tx,ty)` → shape index. No impact on existing behavior.
2. `Validator.__init__`: Two new optional params (`shape_source`, `shape_types`). When None, messages are identical to before.
3. `Validator._shape_context()`: Returns context suffix or empty string.
4. `SURFACE_NAMES`: New dict mapping surface type constants to human-readable names.
5. `main()`: Passes shape info to Validator.

All 70 pre-existing tests pass without modification, confirming backward compatibility.

## Open Concerns

1. **SVG line numbers in validation report**: The acceptance criteria say "line references back to SVG elements where possible." We provide shape index and surface type, not SVG line numbers. `xml.etree.ElementTree` doesn't expose line numbers. Adding them would require switching to a SAX parser or custom TreeBuilder — significant refactor for marginal value. The current approach gives designers actionable context (shape #N, surface type) to locate issues.

2. **Interior fill tiles have angle=0**: The rasterizer sets angle=0 on interior-filled tiles below the surface. This is correct behavior (interior tiles don't have a meaningful surface angle), but it means tests must distinguish surface tiles from fill tiles when checking angle values. The `test_45_slope_angle_approximately_32` test accounts for this.

3. **Floor sensor distance semantics**: The `find_floor()` function returns distance relative to the sensor position (player center + height radius), not the player's y coordinate. This makes distance assertions depend on player size constants. The integration test validates `found=True` and `tile_angle=0` rather than exact distance, which is more robust.

4. **No round-trip with physics simulation**: The integration test loads tiles and runs a floor sensor, but doesn't simulate player movement. A full physics round-trip (player walks on generated terrain) would be a stronger test but depends on player.py state machine stability. This can be added when level.py is implemented (future ticket).

5. **Test execution dependency**: `TestEngineIntegration` imports from `speednik.terrain` and `speednik.physics`. If those modules break, the integration tests are skipped (`@pytest.mark.skipif`), so they won't cause false failures. But this means integration coverage silently degrades if imports fail.
