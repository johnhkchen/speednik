# T-013-03 Research — Re-run Skybridge Audit

## Dependencies Status

Both dependencies are complete (phase: done):

- **T-013-01** (world-boundary-system): Added left/right boundary clamping and pit death
  (y > level_height + 32) in `sim_step()`. Player state set to DEAD, sim.deaths incremented,
  DeathEvent emitted. No respawn — caller's responsibility.

- **T-013-02** (skybridge-collision-gap-fix): Patched `collision.json` at column 11 rows
  31–32 from 0 to 1 (TOP_ONLY). Zero position_y_below_world errors in first 500 frames.

## Skybridge Stage Layout

- **Dimensions**: width=5200, height=896
- **Pit death threshold**: y > 928 (896 + 32)
- **Player start**: x=64, y=480
- **Goal**: x=5158, y=482
- **Checkpoints**: (780, 490), (3980, 490)
- **Springs** (7): x=304/440/592/1200/2016/2832 at y=608; x=3808 at y=692
- **Enemies** (17 total, including boss at 4800,480)
- **Boss**: Egg Piston at x=4800, y=480; 8 HP; spindash-only damage

## Current Audit Results (All 6 Fail)

### Data Collected

| Archetype    | max_x   | deaths | goal  | bugs | key bug reason                |
|-------------|---------|--------|-------|------|-------------------------------|
| Walker      | 583.6   | 0      | False | 1    | min_x < 2500                  |
| Jumper      | 2415.0  | 1      | False | 1    | min_x < 3500                  |
| Speed Demon | 690.9   | 1      | False | 2    | min_x < 5000 + no goal        |
| Cautious    | 292.0   | 0      | False | 1    | min_x < 1200                  |
| Wall Hugger | 583.6   | 0      | False | 1    | min_x < 1500                  |
| Chaos       | 323.2   | 1      | False | 1    | min_x < 600                   |

### Key Observation: No x≈170 Fall-Through

Zero `position_y_below_world` errors in early frames across all archetypes. The col 11
fix (T-013-02) is confirmed effective. Acceptance criterion met.

### Failure Patterns

**Walker/Wall Hugger** (max_x≈583): Walk past the gap, get launched by spring at x≈304,
bounce around, and get stuck oscillating at x≈413 y≈620-626 in a terrain pocket (FULL
solidity tiles col 26-28, rows 38-41). They oscillate between on_ground and jumping
indefinitely. 3799 `on_ground_no_surface` warnings + 174 `quadrant_diagonal_jump` warnings.

**Speed Demon** (max_x=690): Spindashes past the early section, goes airborne at x≈467,
falls off a platform, and dies to pit death at y=928.3 around frame 217. Simulation
continues running 5780 dead frames (player_dead never set to True — see open concern).

**Jumper** (max_x=2415): Best progress. Survives spring bounces, takes damage at x=689
(enemy hit), reaches x=2415 before falling to pit death at frame 1346. One death, 11
warnings (velocity spikes + on_ground_no_surface).

**Cautious** (max_x=292): Too slow and cautious. Walks back and forth near start. Hits
enemies, gets knocked back. Stuck at x≈204 from frame 3000 onward.

**Chaos** (max_x=323): Random inputs, hits enemy, dies to pit at x=323.

### Violation Categories

1. **on_ground_no_surface** (warning): Tiles at (19,31) and (28,31) are None — spring
   tiles at x=304 and x=440 have no collision data. Player reports on_ground=True but
   no tile exists at feet. These are spring object positions, not terrain tiles.

2. **quadrant_diagonal_jump** (warning): Angle oscillation in the terrain pocket at x≈413.
   Quadrant flips between 0 and 2 every frame.

3. **velocity_spike** (warning): From spring launches and spindash releases. Expected.

### Invariant Budget

All violations are warnings, not errors. `invariant_errors_ok=0` is met by all archetypes
(zero invariant errors across the board). The "bugs" are from expectation mismatches
(min_x_progress, require_goal), not invariant errors.

## Run Audit Loop Behavior

The `run_audit` loop in `qa.py:385-392` breaks on `sim.goal_reached or sim.player_dead`.
However, `SimState.player_dead` is never set to True by any code path. When the player
dies from pit death, `player.state = DEAD` is set but `sim.player_dead` stays False. The
`sim_step` early return at line 221 checks `sim.player_dead`, which is always False, so
dead players keep having `player_update` called (no-op since state is DEAD, but sim_step
doesn't stop).

This means: after death, the audit runs for thousands of frames doing nothing. Not a
correctness issue (dead player doesn't move), but a performance waste.

## Test File Structure

`tests/test_audit_skybridge.py` has:
- 6 BehaviorExpectation constants (one per archetype)
- 6 test functions, each calling `run_audit` and asserting `len(bugs) == 0`
- No xfail markers currently
- No pytest.mark decorations

## Relevant Bug Infrastructure

- T-012-04-BUG-01 (skybridge-bottomless-pit-at-x170): phase=done, fixed by T-013-01+T-013-02
- T-013-04 (solid-tile-push-out): phase=implement, may affect terrain pocket stalls
- T-013-05 (loop-and-slope-adhesion): phase=ready, may affect angle oscillation

## Files to Modify

- `tests/test_audit_skybridge.py` — primary target for xfail markers and expectation tuning
- `docs/active/tickets/` — potential new bug tickets for newly discovered issues
