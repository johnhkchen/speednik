# Progress — T-012-02-BUG-03: hillside-no-left-boundary-clamp

## Completed Steps

### Step 1: Add left boundary clamp to `sim_step()` — DONE
- Added 7-line block after `player_update()` call in `simulation.py:233-240`
- Clamps `x` to `max(0.0, x)`, zeros `x_vel` and `ground_speed` when clamped
- Consolidated with existing right-boundary clamp under unified comment

### Step 2: Add left boundary clamp to `_update_gameplay()` — DONE
- Added identical 7-line block after `player_update()` call in `main.py:363-370`
- Maintains parity between headless simulation and live game

### Step 3: Add unit tests — DONE
- Added `test_left_boundary_clamp` in `test_simulation.py`
  - Places player at x=32, holds left for 300 frames, asserts x >= 0 every frame
- Added `test_left_boundary_clamp_zeroes_ground_speed` in `test_simulation.py`
  - Places player at x=16, holds left 60 frames, asserts x==0 and ground_speed >= 0

### Step 4: Update `test_hillside_chaos` xfail — DONE
- Updated xfail reason to reflect that BUG-03 (left clamp) is fixed
- Chaos test still xfails due to remaining bugs: bottom-escape, inside_solid_tile, velocity issues
- These are separate tickets (bottom escape, inside_solid_tile)

### Step 5: Verify no `position_x_negative` violations — DONE
- Ran chaos archetype (seed=42) for 3600 frames
- Result: zero `position_x_negative` violations (was 10,526 before fix)
- Player x range: [0.0, 2415.5] (was [-49488, 64] before fix)

### Step 6: Run test suite — DONE
- `test_simulation.py`: all 34 tests pass (including 2 new ones)
- `test_levels.py`: all pass (xfails unchanged)
- `test_regression.py`: 1 pre-existing failure (skybridge/hold_right_jump, unrelated)

## Deviations from Plan

1. **test_left_edge_escape xfail not removed**: The test uses `run_on_stage()` which calls
   `player_update()` directly (not `sim_step`). The left clamp lives in `sim_step`, so the
   harness-based test still shows the boundary escape. This is by design — the harness is a
   raw physics runner without simulation-level policy.

2. **test_hillside_chaos xfail updated, not removed**: After fixing the left clamp, the chaos
   test reveals other pre-existing bugs (bottom escape, inside_solid_tile) that produce invariant
   errors. The xfail was updated with a new reason reflecting the remaining issues.

3. **test_regression.py position_x_negative exclusion left in place**: The exclusion at line 234
   still serves a purpose for harness-based runs that don't go through `sim_step`.
