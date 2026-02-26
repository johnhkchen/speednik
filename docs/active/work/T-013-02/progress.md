# T-013-02 Progress — skybridge-collision-gap-fix

## Completed

### Step 1: Patch collision.json ✓

Applied fix to `speednik/stages/skybridge/collision.json`:
- `collision[31][11]`: `0` → `1` (NOT_SOLID → TOP_ONLY)
- `collision[32][11]`: `0` → `1` (NOT_SOLID → TOP_ONLY)

Preserved original multi-line formatting. Diff shows exactly two value changes
plus a trailing newline normalization. Verified with assertions:
- `data[31][11] == 1` ✓
- `data[32][11] == 1` ✓
- Adjacent values unchanged ✓
- Rows above/below still empty ✓

### Step 2: Verify test markers ✓

`tests/test_audit_skybridge.py` has no `@pytest.mark.xfail` decorators.
The file is untracked (never committed to HEAD), so no changes needed.

### Step 3: Run skybridge audit tests ✓

All 6 tests still fail, but the failures are now due to **different bugs**,
not the col 11 gap:

- `on_ground_no_surface` at tiles (19,31), (28,31) — springs or platforms
  where the surface tile doesn't exist in tile_map
- `quadrant_diagonal_jump` — angle quadrant oscillation bugs
- `velocity_spike` — sudden velocity changes
- `inside_solid_tile` — player clipping through solid tiles
- `min_x_progress` not met — consequences of the above bugs

Critical verification:
- **`position_y_below_world` findings: 0** — the col 11 gap is fixed
- Walker reaches x=458+ (past the old gap at x≈170) before encountering
  unrelated bugs at x=304+ (spring area)
- No findings in the x=165–195 range (col 11 area)

The remaining test failures are pre-existing bugs tracked by other tickets
(T-013-01 pit death, other collision issues). The col 11 gap fix is
confirmed working.

### Step 4: Regression check ✓

Hillside integration tests: 10/10 pass. No regression from the collision
data change.

## Deviations from Plan

None. The fix was applied exactly as planned.

## Remaining

Nothing. The collision gap fix is complete. The skybridge test failures are
from separate bugs that are out of scope for this ticket.
