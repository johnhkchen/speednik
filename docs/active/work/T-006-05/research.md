# T-006-05 Research: profile2stage overlays, entities, validation

## Scope

Add overlay rasterization (platforms, springs), entity resolution/expansion,
and 9 pre-rasterization validation checks to `tools/profile2stage.py`.

## Current Codebase State

### profile2stage.py (652 lines)

**Data model:**
- `SegmentDef` — segment fields: seg, len, rise, id, amplitude, period, depth, radius
- `ProfileData` — width, height, start_y, segments list (no overlays/entities yet)

**ProfileParser.load():**
- Reads `track`, `width`, `height`, `start_y` from JSON
- Validates segment types against `VALID_SEG_TYPES`
- Auto-generates IDs (`seg_0`, `seg_1`, ...); validates uniqueness
- Returns `ProfileData` — does not parse `overlays` or `entities` keys

**Synthesizer:**
- Cursor state machine: `cursor_x`, `cursor_y`, `cursor_slope`
- Dispatches to `_rasterize_flat/ramp/gap/wave/halfpipe/loop`
- Returns `(grid, pre_warnings)`
- **Does not track segment positions** — cursor_x advances but no mapping
  from segment ID → (start_x, start_y) is stored

**Existing validation (pre-rasterization):**
- `_validate_slopes()` — checks 1 (error >1.0) and 2 (warn >tan30°) for ramps,
  waves, halfpipes
- `_check_slope_discontinuities()` — warns on slope mismatch at segment boundaries
- Loop radius check: in parser (error <32) and synthesizer (warn <64)
- Wave floor clamp: inline during rasterization (warn per affected dx)
- Halfpipe depth: inline during rasterization (error if exceeds floor)

**Missing validation checks from ticket spec:**
- Check 6: Entity segment reference — `at` references unknown segment ID
- Check 7: Entity offset bounds — `offset_x` outside segment x range
- Check 8: Duplicate segment IDs — already exists in parser (line 157-158)
- Check 9: Missing player_start — no entity system yet

**build_meta():**
- Returns dict with `player_start: None`, `checkpoints: []`
- Does not accept entity data

**main():**
- Calls `writer.write(grid, [], meta, all_issues)` — empty entity list

### svg2stage.py Shared Components

**Entity dataclass** (line 123-126):
```python
@dataclass
class Entity:
    entity_type: str
    x: float
    y: float
```

**StageWriter.write()** (line 1002-1007):
- Signature: `write(grid, entities: list[Entity], meta: dict, issues: list[str])`
- `_write_entities()` outputs `[{"type": e.entity_type, "x": round(e.x), "y": round(e.y)}]`
- `_write_meta()` outputs meta dict as-is

**Constants imported by profile2stage:**
- `SURFACE_LOOP`, `SURFACE_SOLID`, `TILE_SIZE`, `TileData`, `TileGrid`, `Validator`, `StageWriter`
- **Not imported:** `SURFACE_TOP_ONLY`, `Entity`

### Test File (945 lines, 52+ tests)

All existing tests pass. Key test patterns:
- `_write_profile(data)` — writes temp JSON, returns path
- `_minimal_profile(**overrides)` — baseline profile dict
- Tests instantiate ProfileParser, Synthesizer, or full pipeline (StageWriter)
- Integration tests check output file existence and JSON validity
- `test_meta_player_start_null` and `test_entities_empty_list` verify current stubs

### Segment Position Tracking Gap

The Synthesizer advances `cursor_x` per segment but never records the mapping
`segment_id → (start_x, start_y)`. Overlay/entity resolution requires this mapping
to anchor world positions. The Synthesizer must build a `segment_positions` dict
during synthesis (or in a pre-pass before rasterization).

### Surface Y Resolution Gap

Entities need `surface_y_at(world_x)` — the ground height at a given pixel column.
This is straightforward for flat/ramp (linear) but complex for wave/halfpipe/loop.
Two approaches: (a) pre-compute a height map during rasterization, or (b) replay
the segment math for a given x. Option (b) is more memory-efficient and avoids
coupling to rasterization order.

### Profile JSON Schema Gap

Current parser reads only `track`. Must add:
- `overlays: list[dict]` — optional, defaults to `[]`
- `entities: list[dict]` — optional, defaults to `[]`
- Per-overlay validation (type, at, offset_x, y_offset, width for platforms)
- Per-entity validation (type, at, offset_x, y_offset, count/spacing for ring_line, subtype for enemy)

### Enemy Subtype Mapping

```
motobug    → enemy_crab
buzzbomber → enemy_buzzer
chopper    → enemy_chopper
```

This is a simple dict lookup. Unknown subtypes should error.

### Overlay Rasterization

Platform overlays are rasterized as flat tile strips:
- Surface type: `SURFACE_TOP_ONLY` if `one_sided`, else `SURFACE_SOLID`
- Height array: `[16] * 16` (full tile height) — flat platform
- Fill below: NO — platforms float; only the platform strip is placed

Spring overlays (`spring_up`, `spring_right`) are entity-only — no tiles.

## Constraints

- `Entity` dataclass from svg2stage has only `entity_type`, `x`, `y` — sufficient
  for all entity types (ring_line expands to individual ring Entity instances)
- `SURFACE_TOP_ONLY` exists in svg2stage (value 2) but is not imported by profile2stage
- Pre-raster validation must run before Synthesizer.synthesize() for checks 1-5, 8
- Checks 6-7, 9 can run after parsing, once segment IDs and entities are known
- Check 8 (duplicate segment IDs) already exists in parser — ticket lists it for completeness

## Key Files

| File | Role |
|------|------|
| `tools/profile2stage.py` | Main file to modify |
| `tools/svg2stage.py` | Imports: Entity, SURFACE_TOP_ONLY (to add) |
| `tests/test_profile2stage.py` | Tests to extend |

## Assumptions

- Overlays and entities are optional JSON keys (backward-compatible)
- Springs are entities, not rasterized geometry
- Platform fill-below is NOT done (platforms float above terrain)
- `y_offset` defaults to 0 if omitted
- `offset_x` defaults to 0 if omitted for entities that don't require it
- Entities with no `y_offset` field sit on the ground surface
