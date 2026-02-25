# Plan — T-010-02: sim-step-and-event-system

## Step 1: Add imports to simulation.py

Add the import aliases for game core event enums (`ObjRingEvent`, `ObjSpringEvent`,
`ObjCheckpointEvent`, `ObjGoalEvent`, `ObjLiquidEvent`), the game core functions
(`check_ring_collection`, `check_spring_collision`, `check_checkpoint_collision`,
`update_pipe_travel`, `update_liquid_zones`, `update_spring_cooldowns`,
`check_goal_collision`, `update_enemies`, `check_enemy_collision`), `InputState`,
and `PlayerState`.

**Verify:** Module imports cleanly (`python -c "import speednik.simulation"`).

## Step 2: Implement sim_step function

Add `sim_step(sim: SimState, inp: InputState) -> list[Event]` after `create_sim()`.

Implementation follows the exact ordering from main.py:_update_gameplay():

1. Death guard: if `player.state == PlayerState.DEAD`, set `sim.player_dead = True`,
   increment `sim.deaths` (only on first detection), return `[DeathEvent()]`.
2. Call `player_update(sim.player, inp, sim.tile_lookup)`.
3. Increment `sim.frame`.
4. Initialize `events: list[Event] = []`.
5. Ring collection → translate `ObjRingEvent.COLLECTED` to `RingCollectedEvent()`.
6. Spring collision → translate `ObjSpringEvent.LAUNCHED` to `SpringEvent()`.
7. Checkpoint collision → translate `ObjCheckpointEvent.ACTIVATED` to `CheckpointEvent()`.
8. Pipe travel → call for side effects, ignore return.
9. Liquid zones → translate `ObjLiquidEvent.DAMAGE` to `DamageEvent()`.
10. `update_enemies(sim.enemies)`.
11. Enemy collision → translate `EnemyEvent.PLAYER_DAMAGED` to `DamageEvent()`.
12. `update_spring_cooldowns(sim.springs)`.
13. Goal collision → if `ObjGoalEvent.REACHED`, set `sim.goal_reached = True`,
    append `GoalReachedEvent()`.
14. Update `sim.max_x_reached = max(sim.max_x_reached, sim.player.physics.x)`.
15. Count `RingCollectedEvent` instances in events, add to `sim.rings_collected`.
16. Return `events`.

**Verify:** `python -c "from speednik.simulation import sim_step"` succeeds.

## Step 3: Write smoke test (60-frame hold_right)

Add `test_sim_step_hold_right_smoke` to `tests/test_simulation.py`:
- `sim = create_sim("hillside")`
- Loop 60 frames with `InputState(right=True)`
- Assert player x increased from start position
- Assert `sim.frame == 60`
- Assert no death/goal flags set

This is the primary acceptance criterion.

**Verify:** `uv run pytest tests/test_simulation.py::test_sim_step_hold_right_smoke -x`

## Step 4: Write death detection test

Add `test_sim_step_death_detection`:
- `sim = create_sim("hillside")`
- Set `sim.player.state = PlayerState.DEAD` directly
- Call `sim_step` → assert returns `[DeathEvent()]`
- Assert `sim.player_dead is True`, `sim.deaths == 1`
- Call again → assert still returns `[DeathEvent()]`, `sim.deaths` still 1

**Verify:** `uv run pytest tests/test_simulation.py::test_sim_step_death_detection -x`

## Step 5: Write frame counter and metrics tests

Add `test_sim_step_frame_counter`:
- Step 10 frames, assert `sim.frame == 10`

Add `test_sim_step_max_x_tracking`:
- Step 60 frames with right input
- Assert `sim.max_x_reached > 0`
- Assert `sim.max_x_reached >= sim.player.physics.x` (non-decreasing)

**Verify:** `uv run pytest tests/test_simulation.py -x`

## Step 6: Run full test suite

Run `uv run pytest tests/ -x` to verify no regressions. Fix any issues.

## Testing Strategy

- **Unit tests**: Death detection, frame counter, metrics — all use direct state
  manipulation on hillside sim.
- **Integration test**: 60-frame smoke test exercises the full sim_step pipeline
  including player physics, terrain collision, and frame counting.
- **No Pyxel test**: Already exists from T-010-01, covers the module.
- **Acceptance criteria coverage**:
  - sim_step advances player physics → smoke test
  - Ring/spring/checkpoint/enemy/goal processing → covered by calling the functions
    in correct order; specific event tests would require positioning player near
    entities which is fragile. The smoke test proves the pipeline runs without error.
  - Death detection → explicit test
  - Metrics tracking → explicit test
  - Order matches main.py → verified by code review in structure phase
  - No Pyxel → existing test
