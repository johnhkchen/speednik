# T-010-07 Research: Reward Signal and Observation Space

## Current State

### SpeednikEnv (`speednik/env.py`)

The Gymnasium environment wrapper was implemented in T-010-06. Key facts:

- **`_compute_reward(events)`** is a placeholder returning `0.0` (line 82–84).
- **`_get_obs()`** delegates to `extract_observation(sim)` — already wired.
- **`observation_space`** uses `Box(low=-np.inf, high=np.inf, shape=(OBS_DIM,))`. The bounds
  are deliberately infinite (standard Gymnasium convention for continuous obs).
- **`_step_count`** tracks frames within the current episode, separate from `sim.frame`.
- **`max_steps`** defaults to 3600 (60 seconds at 60fps).
- Step order: `sim_step` → increment `_step_count` → `_get_obs` → `_compute_reward` → compute
  terminated/truncated. Reward sees post-step state and the events list from that frame.

### Observation Module (`speednik/observation.py`)

T-010-04 implemented a 12-dim observation vector:

| Index | Field             | Normalization         | Range          |
|-------|-------------------|-----------------------|----------------|
| 0     | x_pos             | x / level_width       | [0, 1]         |
| 1     | y_pos             | y / level_height      | [0, 1]         |
| 2     | x_vel             | x_vel / MAX_X_SPEED   | [-1, 1]        |
| 3     | y_vel             | y_vel / MAX_X_SPEED   | [-1, 1]        |
| 4     | on_ground         | bool → float          | {0, 1}         |
| 5     | ground_speed      | gsp / MAX_X_SPEED     | [-1, 1]        |
| 6     | is_rolling        | bool → float          | {0, 1}         |
| 7     | facing_right      | bool → float          | {0, 1}         |
| 8     | surface_angle     | angle / 255           | [0, 1]         |
| 9     | max_progress      | max_x / level_width   | [0, 1]         |
| 10    | distance_to_goal  | (goal_x - x) / w     | varies         |
| 11    | time_fraction     | frame / 3600          | [0, ∞)         |

- `OBS_DIM = 12` exported from `observation.py`. Used in env.py for `observation_space.shape`.
- Observation is already properly shaped and returned as float32 ndarray.
- **No work needed** on observation extraction — it's done and tested.

### Simulation Module (`speednik/simulation.py`)

Relevant state for reward computation:

- **`sim.player.physics.x`** — current x position (pixels).
- **`sim.player.physics.x_vel`** — current horizontal velocity (pixels/frame).
- **`sim.max_x_reached`** — updated at end of `sim_step` (line 279).
- **`sim.goal_reached`** — set to True in step 12 of `sim_step`.
- **`sim.player_dead`** — set to True in step 1 death guard.
- **`sim.level_width`** — level width in pixels for normalization.

Event types emitted by `sim_step`:
- `RingCollectedEvent` — one per ring collected that frame.
- `DamageEvent` — liquid/enemy hit.
- `DeathEvent` — player in DEAD state.
- `GoalReachedEvent` — goal collision.
- `SpringEvent`, `CheckpointEvent` — not needed for reward.

### Timing of max_x_reached update

**Critical detail**: `sim.max_x_reached` is updated at line 279 of `sim_step`, AFTER all
collision checks. When `_compute_reward` runs, `sim.max_x_reached` has already been updated
for the current frame. This means the reward function cannot compute `delta_max(x)` by
comparing pre-step vs post-step `max_x_reached` — it needs to track the previous value itself.

### Constants (`speednik/constants.py`)

- `MAX_X_SPEED = 16.0` — normalization denominator for velocity.
- No existing reward-related constants.

### Existing Tests

- `tests/test_env.py` has 20+ tests. Line 328–332: `test_reward_is_zero_placeholder` asserts
  reward == 0.0. **This test must be removed or replaced** when the real reward is implemented.
- `tests/test_observation.py` — comprehensive, no changes needed.

### Dependency: T-010-06 (done)

SpeednikEnv is fully functional. All we need is to fill in `_compute_reward` and verify
observation space integration.

## Constraints

1. **No Pyxel imports** — env.py must remain headless.
2. **Event type imports** — `RingCollectedEvent` is in `speednik.simulation`, already importable.
3. **MAX_X_SPEED import** — needed for speed bonus normalization. Currently in `speednik.constants`.
4. **Observation space is finalized** — already wired via `extract_observation`. The `_get_obs`
   method and observation_space Box are correct. OBS_DIM swap for T-010-17 remains a one-line
   change in `observation.py`.

## Key Finding: Pre-step max_x tracking

The ticket's pseudocode references `sim.max_x_reached` both before and after the step:
```python
new_max = max(sim.max_x_reached, p.x)
progress_delta = (new_max - sim.max_x_reached) / sim.level_width
```

But by the time `_compute_reward` runs, `sim.max_x_reached` has already been updated by
`sim_step`. We need a `_prev_max_x` instance variable on the env, saved before each `sim_step`
call, to compute the delta correctly.
