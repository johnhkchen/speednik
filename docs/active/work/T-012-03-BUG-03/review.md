# Review — T-012-03-BUG-03: pipeworks-chaos-early-clipping

## Summary of Changes

### Files Modified

| File | Change |
|------|--------|
| `speednik/terrain.py` | Extended `_eject_from_solid()` with horizontal ejection fallback |
| `tests/test_terrain.py` | Added `test_eject_from_solid_horizontal()` |
| `tests/test_audit_pipeworks.py` | Updated `test_pipeworks_chaos` xfail reason |

### What Changed

The `_eject_from_solid()` function in `speednik/terrain.py` previously only
scanned upward (up to 8 tiles) to find free space when the player was inside
a solid tile. If the upward scan failed, it fell back to a fixed `y -= 16`
push which was insufficient for vertically-continuous solid columns.

The fix adds a horizontal ejection pass between the upward scan and the
fallback. When the upward scan exhausts its budget, the function scans left
and right from the player's current column within the tile to find the nearest
non-solid column. This handles the specific failure mode in Pipeworks column 6
(a 1-pixel-wide solid column extending 40 tiles vertically) where upward
escape was impossible but horizontal escape was trivial.

## Test Coverage

### New Tests
- `test_eject_from_solid_horizontal`: Verifies horizontal ejection for a
  vertically-continuous thin wall column (12 tiles tall, only col 4 solid).
  Asserts player is ejected to an adjacent column, set airborne, velocity
  zeroed.

### Existing Test Results
- **1284 passed**, 17 skipped, 18 xfailed, 0 failures.
- `test_pipeworks_walker`: passes (no regression).
- `test_pipeworks_wall_hugger`: passes (no regression).
- `test_pipeworks_chaos`: xfail (progress shortfall only, 0 invariant errors).
- Full terrain test suite: 86 tests pass.

### Audit Results (Chaos seed=42, Pipeworks)
- **Before fix:** 2 `inside_solid_tile` errors at frames 369 and 413.
- **After fix:** 0 invariant errors.
- Remaining finding: max_x≈429 < 800 target (behavioral, not collision).

## Open Concerns

1. **Progress shortfall for Chaos archetype**: The chaos player reaches max_x≈429,
   far below the 800 target. This is not a collision issue — the random movement
   pattern simply doesn't progress far enough. This is a separate concern from
   BUG-03 and is tracked by the xfail annotation.

2. **Horizontal ejection direction bias**: The scan alternates left/right (dc=1,
   then dc=1 right, dc=2 left, etc.) so it finds the nearest free column. For
   the specific Pipeworks case (col 4 of 16), the nearest free column is col 3
   (1px left). This pushes the player slightly leftward, which is the correct
   direction (away from the solid block at column 5).

3. **No horizontal ejection test for fully-solid tiles**: If a tile has all 16
   columns at full height, horizontal ejection also fails, and the existing
   `y -= TILE_SIZE` fallback activates. This is the expected behavior — the
   BUG-02 upward scan handles most fully-solid tiles, and the horizontal
   fallback is only for thin-wall geometry.

## Known Limitations

- The horizontal scan only checks within the current tile. If the player is
  inside a tile where ALL columns are solid, it falls through to the `y -= 16`
  fallback. This is acceptable because fully-solid tiles are handled by the
  upward scan (which finds free space above standard solid blocks).

## No TODOs Remaining

The ticket's stated bug (inside_solid_tile errors at x≈100 in Pipeworks) is
fully resolved. The test suite passes with no regressions.
