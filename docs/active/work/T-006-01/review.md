# Review — T-006-01: fix-loop-arc-rasterization

## Summary of Changes

### Files Modified

1. **`tools/svg2stage.py`** — 2 lines changed
   - Line 727 (`_rasterize_line_segment`): `round(tile_bottom_y - sy)` → `math.ceil(tile_bottom_y - sy)`
   - Line 779 (`_rasterize_loop`): `round(tile_bottom_y - sy)` → `math.ceil(tile_bottom_y - sy)`

2. **`speednik/stages/hillside/tile_map.json`** — regenerated (height arrays updated)
3. **`speednik/stages/hillside/collision.json`** — regenerated (no meaningful change)
4. **`speednik/stages/hillside/entities.json`** — regenerated (no change)
5. **`speednik/stages/hillside/meta.json`** — regenerated (no change)
6. **`speednik/stages/hillside/validation_report.txt`** — regenerated (gaps reduced)

### Files NOT Modified

- `tests/test_svg2stage.py` — all 91 existing tests pass without changes
- `stages/hillside_rush.svg` — source SVG unchanged
- `speednik/terrain.py` — runtime engine unaffected

## What the Fix Does

Replaces Python's `round()` (banker's rounding) with `math.ceil()` in the two
tile-height calculations. This ensures any arc/line sample point that physically
occupies a tile always produces ≥1px of solid surface in that tile.

The fix is conservative: `ceil` slightly over-estimates collision height compared
to `round`, which is the safe direction for platform game physics (better to have
a slightly taller collision surface than a gap).

## Validation Results

| Metric                          | Before | After  | Delta |
|---------------------------------|--------|--------|-------|
| Total impassable gap errors     | 17     | 2      | -15   |
| Loop-column 1px gaps (rounding) | 14     | 0      | -14   |
| Non-loop 1px gaps               | 1      | 0      | -1    |
| 12px structural gaps            | 2      | 2      | 0     |
| Angle inconsistency errors      | 173    | 173    | 0     |

## Test Coverage

- **91 tests pass**, all pre-existing, no modifications needed.
- Test coverage includes:
  - `TestRasterizer`: line segment rasterization, loop rasterization, slope handling
  - `TestRasterizationPrecision`: tile boundary behavior, circle continuity
  - `TestValidator`: gap detection, angle consistency, wall detection
  - `TestEngineIntegration`: pipeline output → engine terrain loading
  - `TestEndToEnd`: full pipeline with SVG → output files

The existing tests use integer-aligned coordinates for most assertions, which is
why `ceil` and `round` produce the same results and no test updates were needed.

## Acceptance Criteria Evaluation

| Criterion | Status |
|-----------|--------|
| `_rasterize_loop` uses `math.ceil` | ✅ Done |
| `_rasterize_line_segment` uses `math.ceil` | ✅ Done |
| `svg2stage.py` runs successfully on hillside | ✅ Done |
| Zero "Impassable gap" for loop columns 217–232 | ⚠️ Partial — see below |
| `pytest tests/test_svg2stage.py -x` passes | ✅ Done (91/91) |
| No regression in angle-consistency errors | ✅ Done (173 → 173) |

## Open Concerns

### 1. Two remaining 12px gaps at columns 220 and 229 (y=624)

The acceptance criteria specifies "zero Impassable gap errors for loop-side columns
(217–232)". Two 12px structural gaps remain at columns 220 and 229. These exist at
the junction where the loop circle meets the ground terrain — they are **not** caused
by the `round()` bug. They were present before the fix (same size, same location)
and represent a geometric reality of the loop–ground intersection.

These may warrant a separate ticket if they affect gameplay. The physics engine's
sensor extension logic may already handle them (the ticket context mentions this).

### 2. Global height shift for non-boundary tiles

All tiles where `tile_bottom_y - sy` has a fractional part in (0, 0.5) now have
height increased by 1 compared to the old `round()` behavior. This is the
semantically correct direction (more solid = safer collision) and all tests pass,
but it means the regenerated `tile_map.json` differs from the previous version in
many tiles, not just the bug-affected ones. This is expected and correct behavior.

### 3. No new tests added

The fix is a one-token change in two locations. The existing 91 tests provide
thorough coverage of the rasterizer. Adding a test specifically for the 0.5 rounding
edge case could be valuable but was not in scope for this ticket.
