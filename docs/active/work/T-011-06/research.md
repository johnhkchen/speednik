# Research — T-011-06 naive-player-regression-suite

## Objective

Understand all components needed for a 3×3 (stage×strategy) parameterized regression
test that combines walkthrough, invariant checking, camera stability, and forward
progress assertions into a single gate file.

## Existing Test Infrastructure

### test_walkthrough.py (T-011-01)
- Uses the **scenario runner** (`speednik.scenarios.run_scenario`) with agent-based execution.
- Caches `ScenarioOutcome` per (stage, strategy) pair in `_OUTCOME_CACHE`.
- `ScenarioOutcome` contains: `name`, `success`, `reason`, `frames_elapsed`, `metrics`,
  `trajectory` (list of `FrameRecord`), `wall_time_ms`.
- `FrameRecord` has: frame, x, y, x_vel, y_vel, ground_speed, angle, on_ground, state,
  action, reward, rings, events (list of event class names as strings).
- Strategies are referenced by agent name: `"hold_right"`, `"jump_runner"`, `"spindash"`.
- Max frames per stage: hillside=4000, pipeworks=5000, skybridge=6000.

### test_camera_stability.py (T-011-04)
- Uses **harness strategies** (`tests.harness` → `speednik.strategies`) — `hold_right()`,
  `spindash_right()` — which are `Callable[[int, Player], InputState]` factories.
- Runs its own sim loop (`run_with_camera`) that steps `sim_step` + `camera_update` together.
- Records `CameraTrajectory` with `CameraSnapshot` per frame (cam_x, cam_y, player_x,
  player_y, player_dead).
- Four assertion helpers: `check_oscillation`, `check_delta_bounds`, `check_level_bounds`,
  `check_player_visible`.
- Only tests 2 strategies (hold_right, spindash_right) × 3 stages.

### test_invariants.py (T-010-09)
- Unit tests for `speednik.invariants.check_invariants()`.
- `check_invariants(sim, snapshots, events_per_frame)` returns `list[Violation]`.
- Snapshots must satisfy `SnapshotLike` protocol: frame, x, y, x_vel, y_vel, on_ground,
  quadrant, state.
- Events must be the raw event objects (not string names).
- Needs a `SimState` with valid `tile_lookup` and level dimensions.

### Strategies — Two APIs

**Harness strategies** (`speednik.strategies`):
- Type: `Strategy = Callable[[int, Player], InputState]`
- Factory functions: `hold_right()`, `hold_right_jump()`, `spindash_right()`
- Used by: test_camera_stability.py, test_geometry_probes.py
- Direct access to Player object (physics, state).

**Agent-based strategies** (`speednik.agents`):
- Type: `Agent` protocol with `act(obs) -> int`, `reset()`.
- Registry names: `"hold_right"` → `HoldRightAgent`, `"jump_runner"` → `JumpRunnerAgent`,
  `"spindash"` → `SpindashAgent`.
- Used by: test_walkthrough.py via scenario runner.
- Only sees observation vector, not raw Player.

**Key difference:** Camera tests use harness strategies with direct sim_step access.
The scenario runner uses agents. The regression test needs both: the scenario runner's
FrameRecord trajectory AND camera tracking from the direct sim loop.

## Core Modules

### speednik/simulation.py
- `create_sim(stage_name)` — loads stage, populates all entities.
- `sim_step(sim, inp)` → `list[Event]` — advances one frame.
- Event types: `RingCollectedEvent`, `DamageEvent`, `DeathEvent`, `SpringEvent`,
  `GoalReachedEvent`, `CheckpointEvent`.
- SimState fields: player, tile_lookup, level_width, level_height, frame, max_x_reached,
  rings_collected, deaths, goal_reached, player_dead.

### speednik/invariants.py
- `check_invariants(sim, snapshots, events_per_frame)` → `list[Violation]`.
- Needs snapshots conforming to `SnapshotLike` (frame, x, y, x_vel, y_vel, on_ground,
  quadrant, state).
- Needs events_per_frame as raw Event objects per frame.
- `FrameRecord` from scenario runner has `events` as string names, NOT raw objects.
  This is a critical incompatibility — cannot directly use scenario runner output.

### speednik/camera.py
- `create_camera(level_width, level_height, player_x, player_y)` → Camera.
- `camera_update(camera, player, inp)` — advances camera one frame.
- Needs raw Player object and InputState, not observation vector.

## Data Compatibility Issues

1. **FrameRecord.events** stores event class names as strings. `check_invariants` needs
   raw Event objects. The regression test must collect raw events alongside FrameRecords.

2. **FrameRecord** lacks `quadrant` field. `SnapshotLike` requires it. The regression
   test must either compute quadrant from angle or capture it alongside.

3. **Camera** needs Player and InputState, not observation. The scenario runner
   doesn't expose these. The regression test must run its own sim loop.

4. **FrameSnapshot** (from strategies.py) has all fields needed for `SnapshotLike`
   including quadrant. But it comes from the harness path, not the agent path.

## Stage Constants

| Stage     | Width | Max Frames |
|-----------|-------|------------|
| hillside  | 4800  | 4000       |
| pipeworks | 5600  | 5000       |
| skybridge | 5200  | 6000       |

## Thresholds from Ticket

- `max_x >= X_THRESHOLD[stage]` — at least 50% of level width.
- `deaths <= MAX_DEATHS[stage][strategy]` — per combo bounds.
- `invariant_errors == 0` — no error-severity violations.
- `camera_oscillations == 0` — no camera wobble.

## Dependencies Satisfied

- T-011-01: test_walkthrough.py ✓
- T-011-02: test_geometry_probes.py ✓ (not directly used here)
- T-011-03: test_geometry_probes.py ✓ (not directly used here)
- T-011-04: test_camera_stability.py ✓
- T-011-05: test_entity_interactions.py ✓ (not directly used here)

## Key Constraint

The regression test must run its own sim loop (not the scenario runner) to capture:
1. Raw Event objects for invariant checking
2. FrameSnapshot-compatible snapshots with quadrant for invariant checking
3. Camera state alongside simulation
4. Forward progress and death metrics

This means the regression test combines the camera stability loop pattern with
invariant checking and metric assertions — a unified sim loop.
