# Progress — T-012-03-BUG-01: pipeworks-slope-wall-blocks-progress

## Completed

### Step 1: Fix tile_map.json

Fixed angle values for 7 tiles at column 32 in `speednik/stages/pipeworks/tile_map.json`:

| Tile | Old angle | New angle | Rationale |
|------|-----------|-----------|-----------|
| (32, 10) | 64 | 0 | Left half is empty (h=0 for cols 0-7); angle=64 caused wall-mode push on player passing through empty space |
| (32, 11) | 64 | 0 | Single-pixel wall at col 8; angle=64 blocked player walking through empty left half |
| (32, 12) | 64 | 32 | Left half has slope surface matching approach tiles; right half is wall. Surface angle matches angle=32 approach |
| (32, 13) | 64 | 0 | Fully solid underground tile (h=[16]*16); flat top surface; matches col 31 underground tiles |
| (32, 14) | 64 | 0 | Same as row 13 |
| (32, 15) | 64 | 0 | Same as row 13 |
| (32, 16) | 64 | 0 | Same as row 13 |

### Step 2: Add regression test — tile angles

Added `test_pipeworks_col32_no_wall_angle` to `tests/test_terrain.py`.
Asserts all 7 tiles (32, rows 10–16) have angle ≤ 32 (floor/slope range).
Passes.

### Step 3: Add integration test — walker passes slope wall

Added `test_pipeworks_walker_passes_slope_wall` to `tests/test_simulation.py`.
Hold-right walker runs 600 frames, asserts max_x > 600.
Walker now reaches x≈3421 in 600 frames. Passes.

### Step 4: Update audit xfail annotations

Updated all 6 xfail reasons in `tests/test_audit_pipeworks.py`:
- Walker/Wall Hugger: reason updated from BUG-01 to BUG-02 (solid tile clipping)
- Jumper/Speed Demon/Cautious: reason updated from BUG-01 to slope difficulty
- Chaos: reason updated from BUG-01 to BUG-03 + insufficient progress
- Module docstring updated to reflect BUG-01 is fixed

All 6 tests still xfail (strict=True) — each archetype still fails for reasons
downstream of the slope wall fix.

### Step 5: Test suite verification

Full test suite: 1274 passed, 11 xfailed (strict), 17 skipped.
4 failures in `test_levels`, `test_regression`, `test_walkthrough`, and
`test_simulation::test_full_sim_pipeworks_liquid_damage` are all pre-existing
from uncommitted working tree changes by other tickets.

## Deviation from Plan

The plan initially targeted only rows 13–16 (fully solid underground tiles).
Testing revealed that rows 10–12 also needed fixing:

- **Row 12** (h=[1,2,2,4,4,6,7,7,16,0,0,0,0,0,0,0]): Left half has a slope
  surface the player walks on. Changed angle from 64 to 32 to match the approach
  slope tiles.

- **Rows 10–11**: These have partial height arrays with solid material only on
  the right half. The left half is empty (h=0). With angle=64, the wall-push
  mechanism pushed the player back even when walking through empty space. Changed
  to angle=0 so the height arrays govern solidity correctly.

This is the same root cause pattern but extends to 7 tiles instead of 4.
