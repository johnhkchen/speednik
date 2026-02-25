# T-006-05 Progress: profile2stage overlays, entities, validation

## Completed Steps

### Step 1: Import and Constant Additions
- Added `SURFACE_TOP_ONLY` and `Entity` to svg2stage imports
- Added `ENEMY_SUBTYPE_MAP`, `VALID_OVERLAY_TYPES`, `VALID_ENTITY_TYPES` constants
- All 64 existing tests pass

### Step 2: Extend ProfileData and ProfileParser
- Added `overlays: list[dict]` and `entities: list[dict]` to ProfileData (with defaults)
- Extended `ProfileParser.load()` with overlay validation (type, at, platform width/one_sided)
- Extended `ProfileParser.load()` with entity validation (type, at, ring_line count/spacing, enemy subtype)
- All existing tests pass (overlays/entities are optional, backward-compatible)

### Step 3: Segment Map and Surface Y
- Added `_build_segment_map()` — replays cursor arithmetic, returns `{id: (start_x, start_y, seg_len)}`
- Added `_surface_y_at()` static method — analytical y computation per segment type
- Called from `synthesize()` before rasterization

### Step 4: Pre-Rasterization Validation (Checks 6, 7, 9)
- Added `_validate_entity_refs()` method
- Check 6: entity/overlay `at` referencing unknown segment ID → ValueError
- Check 7: entity/overlay offset_x outside segment range → warning
- Check 9: missing player_start → warning
- Check 8 (duplicate segment IDs) — already in parser, verified still works

### Step 5: Overlay Rasterization
- Added `_rasterize_overlays()` dispatcher
- Added `_rasterize_platform()` — resolves world position, rasterizes flat strip
- Added `_set_overlay_pixel()` — like `_set_surface_pixel` but accepts surface_type param
- Platform one_sided=true → SURFACE_TOP_ONLY, one_sided=false → SURFACE_SOLID
- Spring overlays skip rasterization (entity-only)

### Step 6: Entity Resolution
- Added `resolve_entities()` standalone function
- ring_line → N individual ring Entity instances with correct spacing
- enemy → mapped via ENEMY_SUBTYPE_MAP
- spring_up/spring_right → Entity from overlays
- player_start/checkpoint/goal → direct Entity creation

### Step 7: Meta Builder and Main Integration
- Updated `build_meta()` to accept entities list
- Scans for player_start → populates meta.player_start
- Scans for checkpoint → populates meta.checkpoints
- Updated `main()` to call resolve_entities and pass entities through

### Step 8: Test Suite
- 19 new tests added across 3 test classes (TestOverlays, TestEntities, TestPreValidation)
- Updated 7 existing build_meta calls to pass empty entity list
- All 83 tests pass (64 existing + 19 new)

### Step 9: Integration Verification
- Full test suite passes: `uv run pytest tests/test_profile2stage.py -x` → 83 passed
- No regressions in existing tests
- Profiles without overlays/entities still work (backward-compatible)

## Deviations from Plan

None. All steps executed as planned.
