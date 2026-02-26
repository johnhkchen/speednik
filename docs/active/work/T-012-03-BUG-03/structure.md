# Structure — T-012-03-BUG-03: pipeworks-chaos-early-clipping

## Files Modified

### 1. `speednik/terrain.py`

**Change:** Extend `_eject_from_solid()` with horizontal ejection fallback.

Current function (lines 761–798):
- Scans upward from player tile for up to 8 tiles.
- If free space found above, places player just below it.
- Fallback: `state.y -= TILE_SIZE`, set airborne.

New behavior after upward scan failure:
- Try horizontal ejection within the current tile.
- For the player's current tile, check columns left and right of
  `col = int(state.x) % TILE_SIZE` for a column where the player's y is above
  the solid region (or height is 0).
- Choose the nearest free column. Push `state.x` to that column position
  (with 1px margin toward center of tile to avoid re-entering solid on next
  frame).
- If horizontal ejection finds a free column, set airborne, zero velocity.
- If horizontal ejection also fails (all columns solid), retain existing
  `y -= TILE_SIZE` fallback.

**No new functions.** The horizontal scan is added as a second fallback path
inside the existing `_eject_from_solid()` function, between the upward scan
loop and the final `y -= TILE_SIZE` fallback.

**Interface changes:** None. `_eject_from_solid()` signature unchanged.

### 2. `tests/test_terrain.py`

**Change:** Add test for horizontal ejection case.

New test: `test_eject_from_solid_horizontal` — constructs a synthetic tile
grid with a vertically-continuous thin solid column (mimics column 6 in
Pipeworks). Places player center inside the solid column. Calls
`resolve_collision()`. Asserts player center is no longer inside solid and
was pushed horizontally.

### 3. `tests/test_audit_pipeworks.py`

**Change:** Remove `xfail` from `test_pipeworks_chaos` if the fix eliminates
all `inside_solid_tile` errors. The test may still fail due to the
`min_x_progress` shortfall (max_x≈488 < 800) — in that case, update the
xfail reason to remove BUG-03 reference and only cite the progress issue.

## Files NOT Modified

- `speednik/invariants.py` — detection logic is correct.
- `speednik/stages/pipeworks/tile_map.json` — tile data is correct.
- `speednik/stages/pipeworks/collision.json` — solidity data is correct.
- `speednik/physics.py` — no movement changes.
- `speednik/simulation.py` — no frame update changes.
- `speednik/player.py` — no state machine changes.
- `speednik/constants.py` — no constant changes.

## Module Boundaries

All changes are within `speednik/terrain.py`'s existing `_eject_from_solid()`
function. No new dependencies. No interface changes. Tests use existing
synthetic grid patterns from `tests/grids.py` or construct their own.

## Ordering

1. Modify `_eject_from_solid()` in terrain.py — add horizontal fallback
2. Add `test_eject_from_solid_horizontal` in test_terrain.py
3. Run full test suite
4. Run pipeworks chaos audit specifically
5. Update test_audit_pipeworks.py xfail as needed
