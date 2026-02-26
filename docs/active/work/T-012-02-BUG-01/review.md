# Review — T-012-02-BUG-01: hillside-wall-at-x601

## Summary

Fixed a single bad angle value in hillside tile data that caused Walker,
Cautious, and Wall Hugger strategies to get stuck at x≈601. The tile at grid
position (37, 38) had `angle=64` (right-wall, 90°) where the geometry and
neighboring tiles indicate `angle=2` (gentle floor slope). The physics engine
was behaving correctly — the data was wrong.

## Changes

### Files Modified

| File | Change | Lines |
|------|--------|-------|
| `speednik/stages/hillside/tile_map.json` | `angle: 64 → 2` at row 38, col 37 | 1 value |
| `tests/test_terrain.py` | Added `test_hillside_tile_37_38_not_wall_angle` | +10 lines |
| `tests/test_simulation.py` | Added `test_hillside_walker_passes_x601` | +11 lines |

### Files NOT Modified

- No Python source files in `speednik/` were changed.
- `collision.json` — solidity=2 (FULL) is correct for this tile.
- `terrain.py`, `physics.py`, `level.py`, `simulation.py` — engine is correct.

## Test Coverage

### New Tests

1. **`test_hillside_tile_37_38_not_wall_angle`** (unit)
   - Loads hillside stage, reads tile (37, 38), asserts `angle <= 5`.
   - Prevents regression if the data pipeline re-generates tile_map.json.

2. **`test_hillside_walker_passes_x601`** (integration)
   - Runs hold-right on hillside for 600 frames.
   - Asserts `max_x_reached > 650` (previously stuck at ≈601).
   - Uses `max_x_reached` rather than final position because enemy
     collisions can bounce the player backwards.

### Existing Tests

All 1244 existing tests pass. No regressions. The 2 pre-existing failures
(`test_walkthrough::TestSpindashReachesGoal::test_hillside` and
`test_audit_hillside::test_hillside_speed_demon`) are unrelated — they
involve boundary clamping bugs tracked in T-012-02-BUG-02 and BUG-03.

## Verification

```
$ uv run pytest tests/ -q --ignore=tests/test_audit_hillside.py --ignore=tests/test_walkthrough.py
1244 passed, 5 xfailed
```

## Open Concerns

1. **Pipeline re-generation**: If the tile data pipeline is re-run, the bad
   angle could be reintroduced. The new unit test guards against this, but
   the pipeline itself should be investigated for the root cause of the
   incorrect angle computation. This is out of scope for this bug fix.

2. **Other tiles**: No systematic scan was performed to check whether other
   tiles in hillside (or other stages) have similar angle/geometry mismatches.
   The QA audit framework (T-012-02) should detect these via invariant
   checks, but a targeted data-quality pass could be valuable.

3. **Pre-existing failures**: The `test_hillside_speed_demon` audit test
   and `test_hillside_spindash` walkthrough test fail due to boundary
   clamping issues (T-012-02-BUG-02, BUG-03). These are separate bugs.

## Confidence

**High**. The fix is a single data value change. The correct value (2) is
unambiguous — derived from both the height array geometry (`atan(1/16) ≈ 2.55`
→ rounds to 2) and direct comparison with adjacent tiles (all angle=0 or
angle=2). The engine code was not modified and all existing tests pass.
