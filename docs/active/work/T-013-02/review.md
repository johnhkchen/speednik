# T-013-02 Review — skybridge-collision-gap-fix

## Summary of Changes

### Files Modified

| File | Change |
|------|--------|
| `speednik/stages/skybridge/collision.json` | Set `[31][11]` and `[32][11]` from `0` to `1` |

Two integer values changed in a 56×325 collision data array. No Python code
modified. No new files created.

### What the Fix Does

The Skybridge Gauntlet collision data had a 16px gap at tile column 11
(px 176–191), rows 31–32. This gap sat between the solid ground block
(cols 0–10, FULL solidity) and the first floating platform (col 12+, TOP_ONLY
solidity). Every archetype fell through this gap at x≈170.

The fix sets col 11 rows 31–32 to `1` (TOP_ONLY), matching:
- The adjacent col 12 surface type
- The existing tile_map.json data for col 11 (which already had TOP_ONLY tiles)

### Root Cause

The SVG source (`stages/skybridge_gauntlet.svg`) has a 32px gap between the
solid ground polygon (ends at x=160) and the first platform polygon (starts at
x=192). The pipeline (`svg2stage.py`) correctly produces col 11 as NOT_SOLID
given this SVG geometry. The tile_map.json had been generated from a different
SVG state that covered col 11, creating a mismatch between collision and
tile_map data. The fix resolves the mismatch by aligning collision.json with
tile_map.json.

## Test Coverage

### Acceptance Criteria Assessment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Walker traverses past x=300 without falling at x≈170 | **Met** | Walker reaches x=458+ before hitting unrelated bugs |
| No `position_y_below_world` errors in first 500 frames | **Met** | 0 below-world findings across all archetypes |
| Collision data has solid tiles at col 11 matching adjacent geometry | **Met** | `collision[31][11] == 1`, `collision[32][11] == 1` verified |

### Test Results

- **Skybridge audit tests (6 tests):** All 6 still fail, but failures are from
  pre-existing bugs unrelated to the col 11 gap:
  - `on_ground_no_surface` at spring tiles (19,31), (28,31)
  - `quadrant_diagonal_jump` oscillation
  - `inside_solid_tile` clipping
  - `min_x_progress` shortfalls (consequence of above bugs)

  **Zero `position_y_below_world` findings** — the col 11 gap is confirmed
  fixed.

- **Hillside integration tests (10 tests):** All pass. No regression.

### Test Gaps

The skybridge audit tests cannot pass until other bugs are fixed:
- Pit death mechanism (T-013-01)
- Spring tile surface data issues
- Quadrant angle oscillation bugs
- Solid tile clipping issues

These are tracked by other tickets and out of scope.

## Open Concerns

1. **SVG source still has the gap.** The SVG at `stages/skybridge_gauntlet.svg`
   has not been updated. If someone reruns `svg2stage.py` from the SVG, the
   collision fix will be overwritten. Consider fixing the SVG as a follow-up.

2. **tile_map.json / collision.json mismatch pattern.** The fact that
   tile_map.json had correct data but collision.json didn't suggests a
   desynchronization in the pipeline. Other columns/stages may have similar
   mismatches. A pipeline audit could surface these.

3. **Remaining skybridge test failures.** All 6 skybridge tests fail due to
   bugs unrelated to the col 11 gap. These need separate fixes before the
   tests can pass.

## Diff Size

The committed diff is 4 lines of semantic change (2 removals, 2 additions)
plus 1 trailing newline normalization. Minimal blast radius.
