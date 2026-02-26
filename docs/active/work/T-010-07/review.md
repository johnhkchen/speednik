# T-010-07 Review: Reward Signal and Observation Space

## Summary of changes

### Files modified

**`speednik/env.py`** — 2 new imports, 1 new instance variable, reward function implementation.

- Added imports: `RingCollectedEvent` from `speednik.simulation`, `MAX_X_SPEED` from
  `speednik.constants`.
- Added `self._prev_max_x` instance variable (float) to track max_x_reached before each
  step, enabling delta_max(x) computation.
- In `reset()`: set `sim.max_x_reached = player.physics.x` to align the initial
  max_x_reached with the spawn position. Set `_prev_max_x` from this value.
- In `step()`: save `self.sim.max_x_reached` to `self._prev_max_x` before calling
  `sim_step`.
- Replaced `_compute_reward` placeholder (returned 0.0) with full implementation:
  - **Progress**: `(max_x_reached - prev_max_x) / level_width * 10.0`
  - **Speed bonus**: `abs(x_vel) / MAX_X_SPEED * 0.01`
  - **Goal completion**: `10.0 + 5.0 * max(0, 1 - step_count/max_steps)`
  - **Death penalty**: `-5.0`
  - **Ring collection**: `+0.1` per `RingCollectedEvent`
  - **Time penalty**: `-0.001` per frame

**`tests/test_env.py`** — removed 1 test, added 6 new tests.

- Removed: `test_reward_is_zero_placeholder` (no longer valid).
- Added:
  - `test_reward_idle_negative_total` — 100 NOOP frames → negative sum
  - `test_reward_hold_right_positive_total` — 100 RIGHT frames → positive sum
  - `test_reward_goal_spike` — goal-frame reward > 10.0
  - `test_reward_death_penalty` — death reward < -4.0
  - `test_reward_ring_collection` — ring collected near player
  - `test_reward_includes_time_penalty` — single NOOP < 0

### Files NOT modified

- `speednik/observation.py` — Already complete from T-010-04. OBS_DIM=12, properly
  normalized, shape matches observation_space.
- `speednik/simulation.py` — No changes needed.
- `speednik/constants.py` — MAX_X_SPEED already exported.

## Acceptance criteria verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `_compute_reward` implements delta_max(x) | PASS | env.py:91–93 |
| Speed bonus rewards horizontal velocity | PASS | env.py:96 |
| Goal completion gives large bonus scaled by time | PASS | env.py:99–101 |
| Death gives negative reward | PASS | env.py:104–105 |
| Ring collection gives small positive reward | PASS | env.py:108–110 |
| Time penalty discourages stalling | PASS | env.py:113 |
| `_get_obs()` returns proper shape matching observation_space | PASS | Pre-existing, tested |
| Observation values normalized (~[-1,1]) | PASS | Pre-existing, tested |
| Idle agent negative total over 100 frames | PASS | test_reward_idle_negative_total |
| Hold-right agent positive total over 100 frames | PASS | test_reward_hold_right_positive_total |
| Goal reached produces reward spike > 10.0 | PASS | test_reward_goal_spike |
| No Pyxel imports | PASS | test_no_pyxel_import_env |
| `uv run pytest tests/ -x` passes | PASS | 935 passed, 5 xfailed |

## Test coverage

- **Reward signal**: 6 new behavioral tests covering all reward components.
- **Observation space**: 12 tests in test_observation.py (unchanged, all pass).
- **Environment integration**: 25 pre-existing tests plus 6 new = 31 total in test_env.py.
- **Gymnasium checker**: `check_env` passes (includes obs/reward type validation).
- **Full suite**: 935 tests pass, no regressions.

## Implementation deviation

**`sim.max_x_reached` initialization**: The simulation factory (`create_sim`) initializes
`max_x_reached = 0.0`, but the player spawns at x=64 on hillside. This caused a spurious
first-frame progress reward of ~0.13 (delta from 0 to 64). Fixed by setting
`sim.max_x_reached = player.physics.x` in `reset()`.

This is a reasonable env-level fix — the env owns the contract that `max_x_reached` starts
at the spawn position. It doesn't modify `create_sim` because other callers (tests,
simulation-level code) may want the raw default.

## Open concerns

1. **`max_x_reached` initialization in simulation.py**: Ideally `create_sim` would
   initialize `max_x_reached` to the spawn x. Currently the env patches this in `reset()`.
   If other consumers of SimState assume max_x_reached starts at 0, they might encounter
   the same first-frame artifact. Low priority — no other consumers compute rewards.

2. **Observation space bounds**: The Box uses `(-inf, +inf)`, which triggers Gymnasium
   warnings. This is intentional — some dims (time_fraction, distance_to_goal) can
   exceed [-1, 1]. The warnings are benign and standard for continuous observation spaces.

3. **Ring collection test**: `test_reward_ring_collection` verifies that rings get collected
   (info["rings"] >= 1) but doesn't precisely isolate the +0.1 delta because progress and
   speed rewards also change between frames. The test confirms the mechanism works; exact
   reward decomposition would require mocking sim_step.
