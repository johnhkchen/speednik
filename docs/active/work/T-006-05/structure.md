# T-006-05 Structure: profile2stage overlays, entities, validation

## Files Modified

### tools/profile2stage.py

**Import additions (line 22-30):**
- Add `SURFACE_TOP_ONLY` and `Entity` to svg2stage imports

**Constants (after line 40):**
- `ENEMY_SUBTYPE_MAP = {"motobug": "enemy_crab", "buzzbomber": "enemy_buzzer", "chopper": "enemy_chopper"}`
- `VALID_OVERLAY_TYPES = {"platform", "spring_up", "spring_right"}`
- `VALID_ENTITY_TYPES = {"player_start", "ring_line", "enemy", "checkpoint", "goal"}`

**ProfileData dataclass (line 59-64):**
- Add `overlays: list[dict]` field (default `[]`)
- Add `entities: list[dict]` field (default `[]`)

**ProfileParser.load() (line 74-167):**
- After segment parsing: parse `data.get("overlays", [])`
  - Validate each overlay has `type` in VALID_OVERLAY_TYPES
  - Validate `at` (str, required), `offset_x` (int, default 0)
  - Platform: validate `width` (int > 0), `y_offset` (int, default 0), `one_sided` (bool, default true)
  - Spring: validate `y_offset` (int, default 0)
- After overlay parsing: parse `data.get("entities", [])`
  - Validate each entity has `type` in VALID_ENTITY_TYPES
  - Common: `at` (str, required), `offset_x` (int, default 0), `y_offset` (int, default 0)
  - ring_line: `count` (int > 0), `spacing` (int > 0)
  - enemy: `subtype` (str, must be in ENEMY_SUBTYPE_MAP)
  - player_start/checkpoint/goal: no extra required fields
- Return ProfileData with overlays and entities

**Synthesizer class:**

New method `_build_segment_map()`:
- Replays cursor arithmetic (no rasterization) over all segments
- Returns `dict[str, tuple[int, float, int]]` — `{id: (start_x, start_y, seg_len)}`
- Stored as `self.segment_map`

New method `_surface_y_at(seg, start_y, dx)`:
- Static method. Returns float surface y for segment type at offset dx
- flat: start_y
- ramp: start_y + seg.rise * dx / seg.len
- wave: start_y + seg.amplitude * sin(2π * dx / seg.period)
- halfpipe: start_y + seg.depth/2 * (1 - cos(2π * dx / seg.len))
- gap/loop: start_y (best-effort for entities)

New method `_validate_entity_refs(pre_warnings)`:
- Check 6: for each entity/overlay, verify `at` is in segment_map. Error if not.
- Check 7: for each entity/overlay, verify offset_x is within [0, seg_len). Warn if not.
- Check 9: if no `player_start` entity exists, append warning.
- Mutates pre_warnings list, raises ValueError for errors.

New method `_rasterize_overlays()`:
- Iterate `self.profile.overlays`
- Platform: resolve (world_x, world_y) via segment_map + _surface_y_at
  - Rasterize flat strip: `width` pixel columns at world_y + y_offset
  - Surface type: SURFACE_TOP_ONLY if one_sided, else SURFACE_SOLID
  - No fill_below (platform floats)
- spring_up/spring_right: skip (entity only)

Modified `synthesize()`:
- Call `_build_segment_map()` first
- Call `_validate_entity_refs(pre_warnings)` after slope validation
- Call `_rasterize_overlays()` after track rasterization
- Return segment_map alongside grid and warnings: `(grid, pre_warnings, segment_map)`
  OR: store segment_map on self and access it externally

New standalone function `resolve_entities(profile, segment_map, surface_y_fn)`:
- Takes profile.entities + profile.overlays (spring types)
- Returns `list[Entity]`
- ring_line: expand to `count` Entity("ring", base_x + i*spacing, world_y)
- enemy: Entity(ENEMY_SUBTYPE_MAP[subtype], world_x, world_y)
- spring_up/spring_right: Entity(type, world_x, world_y) — from overlays
- player_start/checkpoint/goal: Entity(type, world_x, world_y)

**build_meta() (line 584-593):**
- New signature: `build_meta(profile, grid, entities: list[Entity])`
- Scan entities for `player_start` → set `{"x": ..., "y": ...}` or None
- Scan entities for `checkpoint` → list of `{"x": ..., "y": ...}`

**main() (line 600-651):**
- After synthesis: call resolve_entities()
- Pass entities to build_meta()
- Pass entities to writer.write()

### tests/test_profile2stage.py

**New imports:**
- `Entity`, `SURFACE_TOP_ONLY` from svg2stage
- `resolve_entities`, `ENEMY_SUBTYPE_MAP` from profile2stage

**New test class: TestOverlays (~6 tests)**
- test_platform_top_only_tiles — one_sided platform → SURFACE_TOP_ONLY tiles
- test_platform_solid_tiles — one_sided=false → SURFACE_SOLID tiles
- test_platform_world_position — tiles at correct (x, y) from segment anchor
- test_spring_no_tiles — spring overlays don't rasterize
- test_spring_emitted_as_entity — springs appear in entity list
- test_invalid_overlay_type_raises — unknown overlay type errors

**New test class: TestEntities (~8 tests)**
- test_ring_line_expansion — count=5 → 5 ring entities at correct positions
- test_enemy_subtype_mapping — motobug → enemy_crab, etc.
- test_player_start_sets_meta — player_start populates meta.json
- test_checkpoint_in_entities — checkpoint emitted verbatim
- test_goal_in_entities — goal emitted verbatim
- test_missing_segment_id_raises — at references nonexistent segment → error
- test_duplicate_segment_id_raises — (already exists, verify still works)
- test_slope_too_steep_raises — (already exists, verify still works)

**New test class: TestPreValidation (~4 tests)**
- test_entity_unknown_segment_ref_error — check 6
- test_entity_offset_out_of_bounds_warning — check 7
- test_missing_player_start_warning — check 9
- test_validation_report_format — pre-warnings before post-raster output

## Files NOT Modified

- `tools/svg2stage.py` — no changes needed; we only import from it
- `speednik/` game code — not touched by pipeline tool changes
- Other test files — no cross-dependencies

## Public Interface Changes

- `ProfileData` gains `overlays` and `entities` fields
- `Synthesizer.synthesize()` behavior: builds segment_map, validates entity refs
- `build_meta()` gains `entities` parameter
- New exported: `resolve_entities()`, `ENEMY_SUBTYPE_MAP`, `VALID_OVERLAY_TYPES`, `VALID_ENTITY_TYPES`
- ProfileParser accepts overlays/entities keys in JSON (optional, backward-compatible)
