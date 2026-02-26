# Progress: T-012-08-BUG-01 — Hillside Loop Not Traversable

## Summary

Fixed the hillside loop by replacing the hand-placed loop collision tiles
with synthetic `build_loop()` geometry using radius=64 (smaller than the
visual r=128 loop). Added `create_sim_from_lookup()` and `sim_step()` to
`speednik/simulation.py` to support loop audit tests.

## Implementation Details

### Root Cause

The original hillside loop tiles had two problems:
1. The approach ramp (tx=214-216, type=1) used Q1 angles (41-58) with
   slope-shaped height arrays, causing floor-sensor oscillation
2. The loop's outer arc had no Q2 (ceiling) tiles — Q2 existed only on
   the inner ceiling surface (ty=37-38), unreachable from the entry

### Solution: Synthetic r=64 Loop

Used `build_loop(approach_tiles=219, radius=64, ground_row=39, ramp_radius=24)`
to generate collision tiles. Key decisions:

- **Radius 64 instead of 128**: The visual loop is r=128, but r=128 produces
  a very flat bottom arc where the player rides across as flat ground instead
  of being directed up the loop wall. Radius 64 gives tighter curvature that
  the physics engine can follow.

- **Approach tiles preserved**: Original hillside tiles at tx=210-213 are kept
  intact. There's a 5-tile gap (tx=214-218) between the original slope and
  the synthetic loop entry — the player goes briefly airborne crossing this
  gap but lands on the loop wall tiles.

- **Full solidity**: All loop tiles use FULL solidity (not TOP_ONLY for upper
  arc as in the original). This matches build_loop() output and works with
  the SURFACE_LOOP tile exemption in the wall sensor.

### Files Modified

1. **speednik/stages/hillside/tile_map.json** — Replaced loop region tiles
   (tx=214-250) with build_loop() output. Cleared original approach ramp and
   loop tiles, placed synthetic loop circle + entry/exit ramps.

2. **speednik/stages/hillside/collision.json** — Updated solidity values for
   replaced tiles.

3. **speednik/simulation.py** — Added `create_sim_from_lookup()` factory for
   synthetic test setups and `sim_step()` for headless game simulation.

4. **tests/test_loop_audit.py** — Removed xfail marker from
   `TestHillsideLoopTraversal::test_all_quadrants_grounded`.

5. **tests/test_hillside_integration.py** — Updated loop geometry constants
   and test assertions to match the new synthetic loop geometry (r=64,
   cx≈3592, different ramp/loop column ranges, FULL solidity throughout).

## Deviations from Plan

- **Plan called for r=128**: The plan assumed the visual loop radius (128)
  would work with build_loop(). In practice, r=128 produces a bottom arc so
  flat that the player rides across as flat ground. Switched to r=64 which
  gives tighter curvature the physics engine can follow.

- **Approach gap**: The plan expected a smooth connection between the hillside
  approach ramp and the loop entry ramp. In the final implementation, there's
  a ~80px gap where the player is briefly airborne. The player still enters
  the loop correctly by landing on the loop wall tiles.

- **simulation.py changes**: The plan didn't anticipate needing to add
  `sim_step()` and `create_sim_from_lookup()`, but these were needed by the
  test harness (test_loop_audit.py) which imports them.

- **Integration test updates**: The plan didn't call out updating
  test_hillside_integration.py, but the geometry constant changes required it.

## Test Results

- `test_loop_audit.py::TestHillsideLoopTraversal::test_all_quadrants_grounded` — PASS
- `test_loop_audit.py::TestHillsideLoopTraversal::test_exits_loop_region` — PASS
- `test_hillside_integration.py` — 10/10 PASS
- `test_levels.py`, `test_terrain.py`, `test_grids.py`, `test_elementals.py`,
  `test_simulation.py` — All pass (147 pass, 5 xfail)
