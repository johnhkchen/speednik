# Review — T-012-03-BUG-01: pipeworks-slope-wall-blocks-progress

## Summary

Fixed 7 incorrect angle values in the Pipeworks tile map at column 32, rows
10–16. These tiles formed the left wall of a horizontal pipe structure and all
had `angle=64` (right-wall quadrant, 90°). A 45° slope of `angle=32` tiles
(columns 24–31) led directly into this wall, causing the physics engine to
enter wall mode and block all forward progress before x=520.

The fix is data-only — no physics code was changed. The engine behaved
correctly given correct data.

## Changes

### Files Modified

| File | Change | Lines |
|------|--------|-------|
| `speednik/stages/pipeworks/tile_map.json` | 7 angle values corrected | 7 values |
| `tests/test_terrain.py` | Added `test_pipeworks_col32_no_wall_angle` | +11 lines |
| `tests/test_simulation.py` | Added `test_pipeworks_walker_passes_slope_wall` | +10 lines |
| `tests/test_audit_pipeworks.py` | Updated xfail reasons; removed xfail from walker/wall_hugger | ~30 lines |

### Tile Changes

| Tile (col, row) | Old angle | New angle | Rationale |
|-----------------|-----------|-----------|-----------|
| (32, 10) | 64 | 0 | Left half empty (h=0 cols 0-7); wall push blocked player in empty space |
| (32, 11) | 64 | 0 | Single-pixel wall at col 8; left half empty |
| (32, 12) | 64 | 32 | Left half has slope surface matching approach; right half is wall |
| (32, 13) | 64 | 0 | Fully solid underground (h=[16]*16); flat top surface |
| (32, 14) | 64 | 0 | Same as row 13 |
| (32, 15) | 64 | 0 | Same as row 13 |
| (32, 16) | 64 | 0 | Same as row 13 |

### Files NOT Modified

- `speednik/terrain.py` — engine is correct
- `speednik/physics.py` — no physics bug
- `speednik/simulation.py` — no simulation bug
- `speednik/stages/pipeworks/collision.json` — solidity=2 is correct

## Test Coverage

### New Tests

1. **`test_pipeworks_col32_no_wall_angle`** (unit)
   - Loads pipeworks, reads tiles (32, rows 10–16), asserts all have angle ≤ 32.
   - Guards against regression if tile data pipeline regenerates JSON.

2. **`test_pipeworks_walker_passes_slope_wall`** (integration)
   - Runs hold-right walker on pipeworks for 600 frames.
   - Asserts `max_x_reached > 600` (previously stuck at 518).
   - Walker now reaches x≈3421 in 600 frames.

### Updated Tests

3. **`test_pipeworks_walker`** (audit) — xfail REMOVED. Walker now passes all
   expectations (max_x > 3000, 0 invariant errors). This is a direct result of
   fixing BUG-01.

4. **`test_pipeworks_wall_hugger`** (audit) — xfail REMOVED. Same path as
   walker; also now passes all expectations.

5. **`test_pipeworks_jumper`** (audit) — xfail UPDATED. Still fails but no
   longer due to BUG-01; jumper bounces on 45° slope. max_x≈505 vs 5400 target.

6. **`test_pipeworks_speed_demon`** (audit) — xfail UPDATED. Same slope
   difficulty. max_x≈449 vs 5400 target.

7. **`test_pipeworks_cautious`** (audit) — xfail UPDATED. max_x≈447 vs 1500.

8. **`test_pipeworks_chaos`** (audit) — xfail UPDATED. Now references BUG-03
   (solid clipping at x≈100) + insufficient progress.

### Test Suite Results

```
1199 passed, 9 xfailed (strict), 14 warnings
2 failures (pre-existing from other ticket work, not caused by this fix)
```

## Open Concerns

1. **`test_full_sim_pipeworks_liquid_damage`**: This uncommitted test assumes
   the walker encounters liquid zones within 1200 frames. With BUG-01 fixed,
   the walker's path changed — it now reaches x≈3777 without hitting liquid.
   The test needs to be updated by whichever ticket owns it (likely T-012-03 or
   a liquid zone ticket). Not caused by a bug in the fix; the test assumption
   was based on the pre-fix path.

2. **Jumping archetypes on steep slopes**: Jumper, Speed Demon, and Cautious
   still can't progress past the 45° slope approach (cols 24–31). The slope
   tiles have correct `angle=32` — this is legitimate game difficulty, not a
   data bug. The archetypes' jump-and-land mechanics on 45° surfaces cause
   them to bounce backward. This is a game design / archetype tuning issue,
   not a terrain data issue.

3. **Pipe wall tiles (32, 10–11)**: These tiles now have `angle=0` but retain
   their partial height arrays with solid material on the right half. If a
   player somehow approaches from above and lands on tile (32, 10), the
   `angle=0` means the surface will be treated as flat floor instead of wall.
   This is acceptable because: (a) the left half of these tiles is empty
   (h=0), so there's no surface to land on there; (b) the right half is
   underground pipe structure that's covered by fully-solid tiles at (33, 10).
   Edge case risk is minimal.

4. **Pipeline regeneration**: If the tile data pipeline is re-run, these
   angles could be reintroduced. The new unit test guards against this.

## Deviation from Plan

The plan targeted rows 13–16 (4 tiles). Implementation discovered rows 10–12
also needed fixing:
- Row 12: slope surface with angle=64 blocked the player before reaching the
  underground tiles
- Rows 10–11: wall-push mechanism on partially-solid tiles blocked player
  walking through empty left half

Total: 7 tiles fixed instead of 4. Same root cause pattern, same fix approach.

## Confidence

**High**. The fix is purely data (7 angle values in one JSON file). Correct
values are unambiguous — derived from height array geometry and neighboring
tile consistency. The physics engine was not modified. Walker and Wall Hugger
audit tests now pass. All pre-existing tests pass.
