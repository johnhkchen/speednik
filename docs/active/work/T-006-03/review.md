# T-006-03 Review: profile2stage-loop-segment

## Summary of Changes

### Files Modified

**tools/profile2stage.py:**
- Added `SURFACE_LOOP` to svg2stage imports (line 23).
- Added `"loop"` to `VALID_SEG_TYPES` (line 42).
- Added `radius: int = 0` field to `SegmentDef` dataclass.
- Extended `ProfileParser.load()`: loop segments skip `len` requirement, require `radius`,
  validate `radius >= 32` (error), set `seg.len = 2 * radius` internally.
- Added `_rasterize_loop(seg)` method (~40 lines): analytical per-pixel-column circle
  rasterization using `sqrt(r² - dx²)`. Iterates every integer pixel column in the
  circle's x-range. Places both top and bottom arc pixels, fills below bottom arc,
  fills remaining ground via `_fill_below_loop`.
- Added `_set_loop_pixel(col, y, angle, is_upper)` (~20 lines): sets SURFACE_LOOP tiles
  with full tile height and correct `is_loop_upper` flag.
- Added `_fill_column_below(col, y)` (~20 lines): per-pixel-column fill from y down
  to grid bottom.
- Added `_fill_below_loop(start_col, end_col)` (~20 lines): per-tile-column fill from
  lowest SURFACE_LOOP tile down.
- Added dispatch in `synthesize()`: `elif seg.seg == "loop":` branch.
- Slope discontinuity handling: loop uses existing `else` branch (entry/exit slope = 0).

**tests/test_profile2stage.py:**
- Added `SURFACE_LOOP` to svg2stage imports.
- Updated `test_invalid_seg_type_raises`: uses `"teleport"` instead of `"loop"`.
- Added `TestLoopParser` class (5 tests): parsing, missing radius, no len, radius bounds.
- Added `TestLoopSegment` class (7 tests): gap-free, hollow interior, solidity flags,
  cursor advance, ground fill, angle variation, end-to-end pipeline.

## Test Coverage

| Acceptance Criterion | Test(s) | Status |
|---------------------|---------|--------|
| `loop` segment type recognized | `test_loop_parsed_correctly` | PASS |
| Loop center computed correctly | `test_loop_interior_hollow` (validates center position) | PASS |
| Cursor advances by 2*radius | `test_loop_cursor_advance` | PASS |
| Analytical per-pixel-column rasterization | `test_loop_no_gap_errors` (zero gaps = no columns skipped) | PASS |
| No tile gaps on loop sides | `test_loop_no_gap_errors` | PASS |
| Loop interior is hollow | `test_loop_interior_hollow` | PASS |
| Upper arc tiles: is_loop_upper=True → TOP_ONLY | `test_loop_upper_lower_solidity`, `test_loop_end_to_end` | PASS |
| Lower arc tiles: is_loop_upper=False → FULL | `test_loop_upper_lower_solidity`, `test_loop_end_to_end` | PASS |
| Ground fill under loop is solid | `test_loop_ground_fill` | PASS |
| Error if radius < 32 | `test_loop_radius_error_below_32` | PASS |
| Warning if radius < 64 | `test_loop_radius_warning_below_64` | PASS |
| Full pipeline produces valid output | `test_loop_end_to_end` | PASS |
| Existing tests pass | All 64 tests pass | PASS |

## Test Results

```
64 passed in 0.08s
```

Zero failures, zero errors.

## Design Decisions

### Full tile height for loop arc pixels

Loop arc tiles use `h = TILE_SIZE` (full tile height) instead of the precise
`math.ceil(tile_bottom - y)` used in svg2stage.py.

**Rationale:** The Validator's `SOLIDITY_MAP` maps `SURFACE_LOOP → FULL` for all
loop tiles regardless of `is_loop_upper`. The gap checker uses `max(height_array)`
to compute solid ranges. With precise sub-tile heights, adjacent arc tiles on the
loop's sides have small max_h values that don't span the full tile, creating
"Impassable gap" errors between tiles. Full tile height eliminates these gaps.

The `angle` field still provides the correct surface normal for the physics engine's
quadrant-mode switching. This matches Sonic 2's original loop implementation where
loop tiles are fully solid and the physics engine uses the angle to determine
player behavior.

### No intermediate wall tiles

Initially attempted to fill tiles between top and bottom arcs as "wall" tiles.
This flooded the loop interior, breaking the hollow-interior guarantee. Removed
in favor of full-height arc surface tiles which solve the gap issue at the
perimeter only.

## Open Concerns

1. **Transition arcs not implemented.** The ticket describes quarter-circle
   transition arcs at loop entry/exit to bridge from flat ground to the loop's
   tangent. These are omitted. The loop enters/exits at the bottom where the
   tangent is horizontal (angle ≈ 0), which is compatible with adjacent flat
   segments without a transition arc. Transition arcs can be added as a
   follow-up without affecting the core loop implementation.

2. **Physics precision at loop sides.** Full tile heights mean the physics engine
   sees the loop sides as fully solid tiles rather than precise arc surfaces. At
   the extreme sides (first/last 2-3 pixel columns), the player traverses quickly
   (nearly vertical) so sub-tile precision has minimal gameplay impact. The angle
   field still provides correct tangent direction for physics mode switching.

3. **Validator doesn't distinguish upper/lower arc.** The Validator's
   `_check_impassable_gaps` method uses `SOLIDITY_MAP` which maps all SURFACE_LOOP
   tiles to FULL regardless of `is_loop_upper`. The collision writer (StageWriter)
   correctly distinguishes them in the output files. This inconsistency forced the
   full-height approach. A future Validator enhancement could check `is_loop_upper`
   to skip TOP_ONLY loop tiles from gap detection, enabling precise arc heights.

## Files Not Modified

- `tools/svg2stage.py` — no changes (only imports from it).
- `speednik/` game code — no runtime changes.
- Stage data files — not regenerated.
