# T-010-06 Progress: SpeednikEnv Core

## Completed

### Step 1: Add gymnasium dependency
- Ran `uv add gymnasium`. Added gymnasium 1.2.3 + transitive deps (cloudpickle, farama-notifications).
- pyproject.toml updated, uv.lock updated.
- Verified import works.

### Step 2: Implement `speednik/env.py`
- Created `speednik/env.py` with `SpeednikEnv(gym.Env)`.
- `__init__`: accepts stage, render_mode, max_steps. Sets up Box observation space (OBS_DIM,)
  and Discrete(NUM_ACTIONS) action space.
- `reset()`: calls super().reset(seed=seed), creates fresh sim via create_sim, resets
  step_count and _prev_jump_held.
- `step(action)`: delegates to _action_to_input, sim_step, _get_obs, _compute_reward,
  _get_info. Returns Gymnasium 5-tuple.
- `_action_to_input()`: delegates to `action_to_input()` from actions.py, stores
  prev_jump_held on self.
- `_get_obs()`: delegates to `extract_observation()`.
- `_compute_reward()`: returns 0.0 placeholder.
- `_get_info()`: returns dict with frame, x, y, max_x, rings, deaths, goal_reached.
- No deviations from plan.

### Step 3: Write `tests/test_env.py`
- 26 tests covering: spaces, reset, step, jump edge detection, termination (goal/death),
  truncation (max_steps), info dict, multiple episodes, gymnasium env_checker, stage
  parameter, reward placeholder, no-Pyxel.
- No deviations from plan.

### Step 4: Run tests
- `tests/test_env.py`: 26/26 passed.
- Full suite: 930 passed, 5 xfailed, 0 failures. No regressions.
- 3 warnings from env_checker (inf observation bounds, no spec for render modes) — expected
  and correct per spec design.

## Remaining

None. All steps complete.
