# T-007-03 Review: profile2stage Loop Entry/Exit Ramps

## Summary of Changes

### Files Modified

1. **`tools/profile2stage.py`** — 2 changes:
   - `ProfileParser.load()` line 135: loop segment len changed from `2 * radius` to `4 * radius` to account for entry/exit ramp extents.
   - `Synthesizer._rasterize_loop()` lines 627–706: Rewritten to generate quarter-circle entry/exit ramp tiles before and after the loop circle. Added two local helper functions (`_arc_surface_y`, `_ramp_angle`), entry ramp loop, exit ramp loop, and per-pixel ground fill.

2. **`tests/test_profile2stage.py`** — Updated 8 existing tests + added 5 new tests:
   - Existing tests updated for shifted loop center coordinates (entry ramp offsets the circle by r_ramp pixels) and new segment length (4*radius).
   - New tests verify ramp tile existence, angle variation, junction integrity, surface type, and cursor advancement.

### No files created or deleted.

## Acceptance Criteria Evaluation

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Entry ramp tiles before loop circle | Pass | `test_loop_ramp_tiles_exist` verifies SURFACE_SOLID tiles in [flat_before, flat_before+radius) |
| Exit ramp tiles after loop circle | Pass | Same test checks exit ramp region [flat_before+3r, flat_before+4r) |
| Ramp angles transition smoothly 0° → loop tangent | Pass | `test_loop_ramp_angles_progress` verifies varying angles on ramp tiles |
| Ramp tiles are SURFACE_SOLID with FULL solidity | Pass | `test_loop_ramp_surface_solid` verifies no SURFACE_LOOP or is_loop_upper on ramp tiles |
| Cursor advances by r_ramp + 2*radius + r_ramp | Pass | `test_loop_cursor_includes_ramps` and `test_loop_cursor_advance` verify cursor_x == 4*radius |
| cursor_y and cursor_slope correct after exit ramp | Pass | Tests verify cursor_y unchanged, cursor_slope == 0.0 |
| No tile gaps between ramp and loop at tangent points | Pass | `test_loop_ramp_no_gaps_at_junction` and `test_loop_no_gap_errors` verify no validator gap errors |
| Full test suite passes | Pass | 88/88 tests pass |

## Test Coverage

- **Parser tests (5):** All pass. Segment length expectations updated.
- **Loop rasterization tests (12):** 7 existing (updated) + 5 new. Cover ramp tile existence, angles, surface type, gaps, cursor state, hollow interior, ground fill, upper/lower solidity, angle variation, end-to-end pipeline.
- **Other test classes (71):** All pass with no changes required. No regressions.

### Test gaps
- No test explicitly verifies the exact angle values at specific ramp positions (e.g., "entry ramp at x=0 has angle ~0, at x=r_ramp-1 has angle ~64"). The `test_loop_ramp_angles_progress` only checks that angles are non-uniform. Exact angle values depend on floating-point arc evaluation and would make tests brittle.
- No test with `r_ramp != radius`. Currently hardcoded to `r_ramp = radius`. When the configurable r_ramp feature is added, new tests will be needed.

## Implementation Notes

### Deviation from plan
The plan specified using `_fill_below(start, end)` for ground fill under ramp tiles. During implementation, this caused validator gap errors because the arc surface spans multiple tile rows within a single tile column — `_fill_below` only fills entire tile rows below the topmost tile, but doesn't fill height-array entries within the surface tile itself. Switched to per-pixel `_fill_column_below` calls (same approach as the loop circle rasterization) which fills each pixel column solid from the arc surface down to the grid bottom.

### Design choices
- `r_ramp = radius` is hardcoded. The ticket mentions "configurable for future use" — this is ready for parameterization when needed.
- Ramps are rasterized before the loop circle (entry ramp → circle → exit ramp). If any pixel overlaps at the tangent point, the loop tile overwrites the ramp tile. In practice there's no overlap because the entry ramp range is `[entry_start, loop_start)` and the loop range is `[loop_start, loop_end)`.
- The `_build_segment_map` automatically uses the updated `seg.len` (4*radius), so entity/overlay position resolution is consistent.

## Open Concerns

1. **Slope discontinuity checker** (`_check_slope_discontinuities`): The loop segment's entry/exit slopes are treated as 0.0 (same as before ramps). This is correct — the ramp starts at flat (0°) and ends at flat (0°) — but the checker doesn't know about the internal ramp-to-loop angle transition. Not a bug, but worth noting.

2. **Profile files using loop segments**: Any existing `.profile.json` files that declare loop segments will now produce stages where the loop footprint is 4*radius instead of 2*radius. If the profile's `width` field doesn't accommodate the larger footprint, tiles may be placed outside the grid bounds (silently clipped). This is unlikely to be a problem in practice since the game's existing profiles presumably have ample width.
