# T-006-04 Research: profile2stage-wave-halfpipe

## Existing Codebase Map

### tools/profile2stage.py (368 lines)

The pipeline implemented in T-006-02 has three layers:

1. **ProfileParser** — loads `.profile.json`, validates required fields, parses segments
   into `SegmentDef` dataclasses. Currently accepts `flat`, `ramp`, `gap` via
   `VALID_SEG_TYPES` set on line 39.

2. **Synthesizer** — cursor state machine. Holds `cursor_x`, `cursor_y`, `cursor_slope`.
   Dispatches per segment in `synthesize()` (line 140). Each segment handler rasterizes
   into `self.grid` (a `TileGrid`) and advances cursor state.

3. **CLI main()** — glue: parse → synthesize → validate → write.

### Key Constants & Conventions

- `TILE_SIZE = 16` (from svg2stage).
- `SLOPE_WARN_THRESHOLD = tan(30°) ≈ 0.577`, `SLOPE_ERROR_THRESHOLD = 1.0`.
- Heights use `int(round(tile_bottom - y))` in `_set_surface_pixel` (line 251).
  The ticket spec says `math.ceil`; current code uses `round`. This is a discrepancy
  that needs resolution in design.
- `_set_surface_pixel(col, y, angle)` — the per-column rasterizer. Computes `tx`,
  `local_x`, `ty`, `h`, creates/updates TileData, sets height_array and angle.
- `_fill_below(start_col, end_col)` — fills tiles below surface as fully solid.

### SegmentDef Dataclass (line 47)

```python
@dataclass
class SegmentDef:
    seg: str
    len: int
    rise: int  # ramp only
    id: str
```

Only has `rise` for ramp-specific data. `wave` needs `amplitude` and `period`;
`halfpipe` needs `depth`. The dataclass must be extended or replaced.

### Parser Validation Flow

`ProfileParser.load()` (line 70):
- Checks `seg` against `VALID_SEG_TYPES` set.
- Ramp-specific: checks for `rise` field.
- No per-type parameter validation for non-ramp types.

### Slope Validation

`_validate_slopes()` (line 158) only checks ramp segments. The wave and halfpipe
segments have analytic max-slope formulas:
- wave: `2π * amplitude / period`
- halfpipe: `π * depth / (2 * len)`

These need their own validation path since they aren't simple `rise/len` ratios.

### Slope Discontinuity Check

`_check_slope_discontinuities()` (line 177) computes exit slope for each segment:
flat=0, ramp=rise/len. Gaps reset tracking. Wave and halfpipe have analytically
determined exit slopes that must be threaded into this check.

### Rasterization Pattern

Current segments (`flat`, `ramp`) iterate pixel columns and call `_set_surface_pixel`
per column. The ticket proposes a shared `_rasterize_height_profile(profile_fn, ...)`
utility. Currently no such abstraction exists — each segment handler is bespoke.

### TileData & height_array

From svg2stage: `height_array` is a list of 16 ints. Each element is the surface
height (from tile bottom, 0–16) at that sub-pixel column. `_set_surface_pixel`
computes `h = int(round(tile_bottom - y))` clamped to [0, 16].

### Tests (tests/test_profile2stage.py, 643 lines)

Comprehensive tests for flat, ramp, gap, cursor state, slope validation, integration.
Imports from `profile2stage` and `svg2stage`. Uses `_write_profile()` and
`_minimal_profile()` helpers.

### Floor Boundary

`height - TILE_SIZE` is the floor clamping threshold. For default height=720,
floor = 704. For test height=160, floor = 144.

## Constraints & Assumptions

1. `wave` and `halfpipe` are purely analytic — no pixel-sampled walk needed.
2. Both use the same `_set_surface_pixel` + `_fill_below` pattern as existing segments.
3. The ticket explicitly requests a shared `_rasterize_height_profile` utility.
4. `SegmentDef` must carry segment-specific parameters (amplitude, period, depth).
5. The parser must validate segment-specific required fields.
6. Slope validation must handle analytic max slopes, not just `rise/len`.
7. Exit slope/y for discontinuity checking must use analytic derivatives.
8. `math.ceil` is specified in the ticket for height calculations; current code
   uses `round`. The ticket controls — use `math.ceil` for new code.
9. Floor clamping is wave-only (halfpipe validates depth fits before rasterizing).
10. The `angle` byte for curved segments: the instantaneous slope changes per column.
    Each column gets its own angle computed from the derivative at that point.

## Open Questions for Design

- Should `_rasterize_height_profile` replace `_rasterize_flat` and `_rasterize_ramp`
  too, or only be used by wave/halfpipe? Ticket says "optional for this ticket."
- How to extend `SegmentDef` — add optional fields, or use a dict/union type?
- Should wave angle vary per-column (accurate) or use a single average (simpler)?
  The instantaneous slope changes continuously, so per-column is correct.
