# Review — T-012-04-BUG-01: skybridge-bottomless-pit-at-x170

## Summary

Fixed a missing collision tile at column 11 in Skybridge Gauntlet that created a
bottomless pit at x~170, the first obstacle in the stage. All 6 player archetypes
were falling through and (prior to T-013-01's pit death fix) never dying. The fix
closes the gap by adding tile data to column 11 and normalizing the trailing-edge
tile at column 10.

## Files Changed

| File | Change |
|------|--------|
| `speednik/stages/skybridge/tile_map.json` | Added tiles at (31,11) and (32,11); fixed trailing-edge heights at (31,10) and (32,10) |
| `speednik/stages/skybridge/collision.json` | Set collision at (31,11) and (32,11) from 0 to 1 (TOP_ONLY) |
| `tests/test_audit_skybridge.py` | Removed 6 xfail decorators, removed BUG-01 docstring note, removed unused pytest import |

No engine code (simulation.py, player.py, terrain.py, etc.) was modified.

## What the Fix Does

- Fills the gap at tile column 11 (px 176-192) in rows 31-32 with solid bridge tiles
- Normalizes column 10's height_array from [12,0,...,0] to all-12 (row 31) and
  [16,0,...,0] to all-16 (row 32), removing the trailing-edge slope that made the
  effective gap 31px wide instead of 16px
- The walking surface now runs continuously from col 0 through col 11, with col 19
  (px 304-320) as the first real gap

## Test Coverage

### Direct verification
- Smoke test confirms walker traverses x=170 at y=480 (on_ground=True), 0 deaths

### Regression
- Skybridge audit tests: All 6 tests run without xfail. They currently fail for
  **unrelated** reasons (later gaps at tiles 19/28 causing on_ground_no_surface
  violations, quadrant_diagonal_jump issues at x~331). These are separate bugs.
- Hillside tests: Unaffected (1 pre-existing failure, 11 xfails — same as before)
- Pipeworks tests: Unaffected (no shared data)

### Coverage gaps
- No unit test specifically asserts "col 11 has valid tile data." The smoke test
  validates behavior (player stays on ground at x=170) which is sufficient.
- The skybridge audit tests serve as integration coverage once their own bugs are
  resolved in separate tickets.

## Open Concerns

1. **Skybridge audit tests still fail.** The xfails were removed because the
   T-012-04-BUG-01 bug is fixed, but other bugs surface immediately:
   - `on_ground_no_surface` at tile (19,31) and (28,31) — the next gaps in the level
   - `quadrant_diagonal_jump` violations at x~331 — likely a terrain/angle issue
   These need separate bug tickets (T-012-04-BUG-02+).

2. **Pit death mechanism dependency.** This fix assumes T-013-01's pit death code is
   merged (simulation.py lines 246-252, PIT_DEATH_MARGIN=32). Without it, falling
   into later intentional gaps would still cause the "never dies" symptom. The pit
   death code IS present in the current codebase.

3. **Column 10 trailing edge removal.** The original col 10 had angle=192 and
   heights=[12,0,...,0], which created a visual/physics slope-down effect at the
   bridge edge. Changing it to flat (angle=0, all-12) removes that slope. If the
   trailing edge was intentional visual design, it could be restored by adding it
   to col 11 instead (angle=192 on col 11, with col 12 already having angle=64
   as the leading edge of the next segment). However, this would re-narrow the
   solid surface at the transition. The flat approach is simpler and safe.

## Conclusion

The root cause — missing tile data at column 11 — is fixed. The "never dies" aspect
was independently fixed by T-013-01. The remaining skybridge audit failures are
separate issues unrelated to this ticket's scope.
