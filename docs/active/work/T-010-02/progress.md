# Progress — T-010-02: sim-step-and-event-system

## Completed

### Step 1: Imports (already done by T-010-01)

All imports were already present in `speednik/simulation.py` from T-010-01:
- `InputState`, `PlayerState`, `player_update` from physics/player modules
- All object functions with aliased event enums (`ObjRingEvent`, `ObjSpringEvent`, etc.)
- `update_enemies`, `check_enemy_collision`, `EnemyEvent` from enemies module

No additional imports needed.

### Step 2: Implement sim_step

Added `sim_step(sim: SimState, inp: InputState) -> list[Event]` at line 177 of
`speednik/simulation.py`, after `create_sim()`.

Implementation follows the exact `_update_gameplay()` order from `main.py` lines 343–442:

1. Death guard: check `player.state == DEAD`, set `sim.player_dead`, increment `sim.deaths`
   (only on first detection), return `[DeathEvent()]`. No physics on dead frames.
2. `player_update(sim.player, inp, sim.tile_lookup)` — full player physics.
3. `sim.frame += 1` — frame counter.
4. Ring collection → translate `ObjRingEvent.COLLECTED` to `RingCollectedEvent()`.
5. Spring collision → translate `ObjSpringEvent.LAUNCHED` to `SpringEvent()`.
6. Checkpoint collision → translate `ObjCheckpointEvent.ACTIVATED` to `CheckpointEvent()`.
7. Pipe travel → side effects only (no sim events).
8. Liquid zones → translate `ObjLiquidEvent.DAMAGE` to `DamageEvent()`.
9. `update_enemies(sim.enemies)` — enemy behavior updates.
10. Enemy collision → translate `EnemyEvent.PLAYER_DAMAGED` to `DamageEvent()`.
11. `update_spring_cooldowns(sim.springs)` — spring cooldown timers.
12. Goal collision → if `ObjGoalEvent.REACHED`, set `sim.goal_reached`, append `GoalReachedEvent()`.
13. Metrics: update `max_x_reached`, count `RingCollectedEvent` instances for `rings_collected`.

Total: ~60 lines of implementation.

### Step 3: Smoke test (60-frame hold_right)

Added `test_sim_step_hold_right_smoke` — creates hillside sim, runs 60 frames with
`InputState(right=True)`, asserts player x increased, frame == 60, no death/goal flags.

Passes.

### Step 4: Death detection tests

Added three tests:
- `test_sim_step_death_detection`: manually set DEAD state, step, assert DeathEvent + flags
- `test_sim_step_death_persistent`: dead stays dead, deaths not re-incremented
- `test_sim_step_death_no_physics`: dead frame doesn't advance counter or position

All pass.

### Step 5: Frame counter and metrics tests

- `test_sim_step_frame_counter`: 10 steps → frame == 10
- `test_sim_step_max_x_tracking`: 60 steps right → max_x_reached > 0 and >= current x
- `test_sim_step_returns_list`: basic type check
- `test_sim_step_enemy_update`: crab patrol changes x over 10 frames
- `test_sim_step_goal_detection`: teleport to goal, step, assert GoalReachedEvent + flag

All pass.

### Step 6: Full test suite

`uv run --extra dev pytest tests/ -x` → **830 passed, 5 xfailed** in 1.95s.

No regressions.

## Deviations from Plan

None. Implementation followed the plan exactly.

## Remaining

Implementation complete. All acceptance criteria satisfied. Proceeding to Review phase.
