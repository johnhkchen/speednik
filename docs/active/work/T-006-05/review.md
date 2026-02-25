# T-006-05 Review: profile2stage overlays, entities, validation

## Summary of Changes

### Files Modified

**tools/profile2stage.py** (652 → 983 lines, +331 lines)
- Added imports: `SURFACE_TOP_ONLY`, `Entity` from svg2stage
- Added constants: `VALID_OVERLAY_TYPES`, `VALID_ENTITY_TYPES`, `ENEMY_SUBTYPE_MAP`
- Extended `ProfileData` with `overlays` and `entities` fields (default `[]`)
- Extended `ProfileParser.load()` with overlay/entity parsing and validation
- Added `Synthesizer._build_segment_map()` — maps segment IDs to (start_x, start_y, seg_len)
- Added `Synthesizer._surface_y_at()` — analytical surface y per segment type
- Added `Synthesizer._validate_entity_refs()` — checks 6, 7, 9
- Added `Synthesizer._rasterize_overlays()` and `_rasterize_platform()`
- Added `Synthesizer._set_overlay_pixel()` — surface pixel with configurable surface type
- Added `resolve_entities()` — resolves all entities/spring-overlays to world coordinates
- Updated `build_meta()` — accepts entities, populates player_start and checkpoints
- Updated `main()` — integrates entity resolution into pipeline

**tests/test_profile2stage.py** (1207 → 1736 lines, +529 lines)
- Updated imports to include new symbols
- Fixed 7 existing `build_meta()` calls to pass empty entity list
- Added `TestOverlays` class (6 tests)
- Added `TestEntities` class (7 tests)
- Added `TestPreValidation` class (6 tests)

### No files created or deleted.

## Acceptance Criteria Coverage

| Criterion | Status | Test Coverage |
|-----------|--------|---------------|
| Platform overlay → TOP_ONLY or FULL tiles | Done | `test_platform_top_only_tiles`, `test_platform_solid_tiles` |
| spring_up/spring_right → entities.json | Done | `test_spring_emitted_as_entity` |
| All entity types resolve via at + offset_x + y_offset | Done | All entity tests verify positions |
| ring_line expands to N rings | Done | `test_ring_line_expansion` (count=5) |
| Enemy subtype mapping | Done | `test_enemy_subtype_mapping` (all 3 subtypes) |
| player_start → meta.json | Done | `test_player_start_sets_meta` |
| checkpoint/goal emitted verbatim | Done | `test_checkpoint_in_entities`, `test_goal_in_entities` |
| 9 pre-rasterization checks | Done | Checks 1-5 existed; 6-9 added with tests |
| Errors abort (exit non-zero) | Done | `test_missing_segment_id_raises`, `test_slope_too_steep_raises` |
| Warnings in validation_report.txt | Done | `test_validation_report_format` |
| All tests pass | Done | 83/83 passed |

## Test Coverage

- **83 total tests** (64 existing + 19 new), all passing
- **TestOverlays (6):** platform TOP_ONLY, platform SOLID, world position, spring no tiles, spring as entity, invalid type
- **TestEntities (7):** ring_line expansion, enemy mapping, player_start meta, checkpoint, goal, missing segment ref, steep slope regression
- **TestPreValidation (6):** entity unknown segment, overlay unknown segment, offset out-of-bounds warning, missing player_start warning, validation report format, duplicate segment ID

### Coverage gaps (minor):
- No test for platform on non-flat segment (e.g., ramp surface). The `_surface_y_at` analytical math is tested implicitly via entity positioning on flat segments, but a direct test on a ramp anchor would strengthen coverage.
- No end-to-end test that writes entities.json and verifies its contents via StageWriter. Current tests verify entity resolution returns correct Entity objects, and existing integration tests verify file writing works, but the two aren't combined in a single test for this ticket's features.
- No test for negative `offset_x` warning (offset_x < 0 case of check 7). The test covers offset_x > seg_len but not the negative case.

## Open Concerns

1. **Segment map cursor tracking**: `_build_segment_map()` replays cursor arithmetic separately from the actual rasterization loop. If a future segment type modifies cursor_y in a way not captured by the map builder (e.g., a new segment type with non-trivial exit y), the map will diverge from actual rasterization. This is a maintenance hazard but acceptable for now since both paths use the same formulas.

2. **Platform fill-below not done**: Per design, platforms float (no `_fill_below` call). This is correct for one-sided platforms but may look odd for solid platforms hovering above empty space. The game engine's collision system handles this fine, but visual appearance in the tile map may surprise level designers.

3. **Homing chain reference frame**: Deferred per ticket spec (noted as "spec only"). No implementation or validation for homing chains.

4. **Existing pre-raster checks (1-5) message format**: The ticket spec defines specific error message formats (e.g., "ramp {id}: slope {val:.2f} exceeds maximum passable ratio 1.0") but the existing implementation uses slightly different wording. This predates this ticket and was not changed to avoid breaking existing tests/behavior.
