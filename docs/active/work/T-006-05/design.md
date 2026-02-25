# T-006-05 Design: profile2stage overlays, entities, validation

## Problem

profile2stage currently handles only the track layer. It needs overlay
rasterization, entity resolution, and pre-rasterization validation to
complete the three-layer pipeline.

## Design Decisions

### D1: Segment Position Tracking

**Options:**
A. Build `segment_positions` dict in a pre-pass before rasterization
B. Record positions during Synthesizer.synthesize() as segments are processed
C. Replay segment math on-demand per entity lookup

**Choice: A — pre-pass.** The pre-pass is simple cursor arithmetic (no
rasterization), produces `{seg_id: (start_x, start_y)}` for all segments,
and decouples position resolution from rasterization order. Pre-raster
validation (checks 6-7) also needs this data before synthesis runs.

Implementation: `Synthesizer._build_segment_map()` returns
`dict[str, tuple[int, float, int]]` mapping `seg_id → (start_x, start_y, seg_len)`.
Called once from `synthesize()` before the rasterization loop.

### D2: Surface Y at Arbitrary X

**Options:**
A. Pre-compute full pixel-column height map during rasterization
B. Compute surface_y analytically from segment parameters + offset_x

**Choice: B — analytical.** Each segment type has a closed-form y(dx):
- flat: `cursor_y`
- ramp: `cursor_y + rise * dx / len`
- gap: `cursor_y` (no surface, but use last cursor_y)
- wave: `cursor_y + amplitude * sin(2π * dx / period)`
- halfpipe: `cursor_y + depth/2 * (1 - cos(2π * dx / len))`
- loop: `cursor_y` (entities on loop surface are unusual; use entry y)

Implementation: `_surface_y_at(seg: SegmentDef, start_y: float, dx: int) -> float`
static method. Handles each segment type. Used by both overlay and entity resolution.

### D3: Overlay and Entity Data Flow

**Pipeline order:**
1. `ProfileParser.load()` — parse JSON including overlays/entities
2. `Synthesizer.__init__()` — build segment map
3. Pre-raster validation (checks 6-9 using segment map + parsed overlays/entities)
4. `Synthesizer.synthesize()` — rasterize track + overlays
5. Entity resolution — resolve all entities to world coordinates
6. Build meta — extract player_start/checkpoints from resolved entities
7. Post-raster validation (Validator)
8. Write output

Overlays are processed DURING synthesis (after track, on the same grid).
Entities are resolved AFTER synthesis (they don't affect the grid).

### D4: ProfileData Extensions

Add to `ProfileData`:
- `overlays: list[dict]` — raw overlay dicts from JSON
- `entities: list[dict]` — raw entity dicts from JSON

Keep them as raw dicts (not dataclasses). The overlay/entity schemas are
heterogeneous (different fields per type), and creating dataclasses for
each would be over-engineering. Validation happens in the parser.

### D5: Overlay Rasterization

Platform overlays are rasterized after track segments, using the segment map
for positioning. They call `_set_surface_pixel` with the appropriate surface
type (TOP_ONLY or SOLID) and `_fill_below` is NOT called (platforms float).

Implementation: `Synthesizer._rasterize_overlays()` iterates overlays,
dispatches by type. Platform: compute world (x, y), rasterize flat strip.
Spring: skip (entity only).

### D6: Entity Resolution

`resolve_entities()` function takes parsed entities, segment map, and profile,
returns `list[Entity]`. Handles:
- `ring_line` → expand to N individual `ring` entities
- `enemy` → map subtype via `ENEMY_SUBTYPE_MAP`
- `spring_up`/`spring_right` → pass through as entities
- `player_start`, `checkpoint`, `goal` → pass through

Also processes spring-type overlays as entities.

### D7: Pre-Rasterization Validation Consolidation

Current state: checks 1-5 are scattered across `_validate_slopes()`,
`_check_slope_discontinuities()`, inline wave/halfpipe code, and parser.

For this ticket, add checks 6-9 only (the new ones). Existing checks 1-5
remain where they are. New checks:
- Check 6 (entity segment ref): validate in `_validate_entity_refs()`
- Check 7 (entity offset bounds): validate in `_validate_entity_refs()`
- Check 8 (duplicate IDs): already an error in parser — no change needed
- Check 9 (missing player_start): check after entity resolution

New method: `_validate_entity_refs(segment_map, entities, overlays)` — called
from synthesize() after building segment map, before rasterization.

### D8: Import Additions

Add to imports from svg2stage: `SURFACE_TOP_ONLY`, `Entity`.

## Rejected Approaches

- **Overlay dataclass hierarchy:** Over-engineering for 3 overlay types.
  Raw dicts with validation are simpler and match the JSON schema directly.
- **Height map pre-computation:** Memory cost (width pixels × float) and
  couples entity resolution to rasterization. Analytical computation is
  cleaner and zero-allocation.
- **Entity resolution during rasterization:** Entities don't affect the grid,
  so mixing them into the rasterization loop adds complexity with no benefit.
- **Separate validation module:** Only 4 new checks. A separate module
  would be premature — keep validation co-located in the Synthesizer.

## Error vs Warning Strategy

Per ticket spec:
- Errors → raise ValueError → abort synthesis → exit 2
- Warnings → collect in list → include in validation_report.txt
- Entity segment ref (check 6) → error (aborts)
- Entity offset bounds (check 7) → warning (allows adjacent segment reach)
- Missing player_start (check 9) → warning (meta.json gets null)
