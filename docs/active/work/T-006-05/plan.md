# T-006-05 Plan: profile2stage overlays, entities, validation

## Step 1: Import and Constant Additions

- Add `SURFACE_TOP_ONLY` and `Entity` to svg2stage imports
- Add `ENEMY_SUBTYPE_MAP`, `VALID_OVERLAY_TYPES`, `VALID_ENTITY_TYPES` constants
- Verify: existing tests still pass (no regressions from import changes)

## Step 2: Extend ProfileData and ProfileParser

- Add `overlays: list[dict]` and `entities: list[dict]` to ProfileData
- Extend `ProfileParser.load()` to parse and validate overlays array
  - Type validation, required fields per overlay type
  - Default values for optional fields (offset_x, y_offset)
- Extend `ProfileParser.load()` to parse and validate entities array
  - Type validation, required fields per entity type
  - ring_line: count, spacing required
  - enemy: subtype required, must be in ENEMY_SUBTYPE_MAP
- Verify: existing tests pass; new profiles with overlays/entities parse correctly

## Step 3: Segment Map and Surface Y

- Add `_build_segment_map()` to Synthesizer
  - Walk segments, accumulate cursor_x/cursor_y positions
  - Return `{seg_id: (start_x, start_y, seg_len)}`
- Add `_surface_y_at()` static method
  - Compute y analytically per segment type at a given dx offset
- Call `_build_segment_map()` at start of `synthesize()`
- Verify: segment map correctly maps IDs to positions (unit test)

## Step 4: Pre-Rasterization Validation (Checks 6, 7, 9)

- Add `_validate_entity_refs()` method
  - Check 6: each overlay/entity `at` field → must exist in segment_map → ValueError
  - Check 7: each overlay/entity offset_x → warn if outside [0, seg_len)
  - Check 9: warn if no player_start in entities list
- Call from `synthesize()` after building segment map, before rasterization
- Verify: invalid segment refs raise; out-of-bounds offsets warn; missing player_start warns

## Step 5: Overlay Rasterization

- Add `_rasterize_overlays()` method
  - Platform: resolve world position, rasterize flat strip with correct surface type
  - Use `_set_surface_pixel` but with SURFACE_TOP_ONLY/SURFACE_SOLID
  - Need a variant that sets surface_type (current _set_surface_pixel hardcodes SURFACE_SOLID)
- Add `_set_overlay_pixel()` — like _set_surface_pixel but accepts surface_type param
- Call `_rasterize_overlays()` from `synthesize()` after track rasterization
- Verify: platform tiles at correct position with correct surface type

## Step 6: Entity Resolution

- Add `resolve_entities()` standalone function
  - Process profile.entities: resolve each to world (x, y) via segment_map + surface_y
  - ring_line: expand to N ring Entity instances
  - enemy: map subtype via ENEMY_SUBTYPE_MAP
  - player_start/checkpoint/goal: direct Entity creation
- Process spring overlays: emit as Entity instances
- Verify: ring_line expansion correct; subtype mapping correct; spring entities emitted

## Step 7: Meta Builder and Main Integration

- Update `build_meta()` to accept entities list
  - Scan for player_start → set meta.player_start
  - Scan for checkpoint → populate meta.checkpoints list
- Update `main()`:
  - synthesize() now provides segment_map (via self)
  - Call resolve_entities() after synthesis
  - Pass entities to build_meta()
  - Pass entities to writer.write()
- Verify: end-to-end pipeline produces correct entities.json and meta.json

## Step 8: Test Suite

New tests covering acceptance criteria:
1. Platform overlay → TOP_ONLY tiles at correct world position
2. Platform overlay → SOLID tiles when one_sided=false
3. ring_line N=5 → 5 ring entities at correct positions
4. Enemy subtype mapping (all 3 subtypes)
5. player_start → populates meta.json
6. checkpoint/goal → emitted to entities.json
7. Spring overlays → emitted as entities, no tiles
8. Missing segment ID in `at` → error
9. Duplicate segment ID → error (existing, re-verify)
10. Slope-too-steep → error (existing, re-verify)
11. Entity offset out-of-bounds → warning
12. Missing player_start → warning
13. Validation report format: pre-warnings then post-raster

Run: `uv run pytest tests/test_profile2stage.py -x`

## Step 9: Integration Verification

- Run full test suite
- Fix any failures
- Verify backward compatibility (profiles without overlays/entities still work)

## Testing Strategy

- **Unit tests:** Parser validation, segment map building, surface_y computation,
  entity resolution, subtype mapping, ring_line expansion
- **Integration tests:** Full pipeline with overlays+entities produces correct
  output files (entities.json, meta.json, validation_report.txt)
- **Regression tests:** Existing 52+ tests must all still pass
- **Edge cases:** Empty overlays/entities, offset_x=0, negative y_offset,
  spring overlays (entity-only, no tiles)
