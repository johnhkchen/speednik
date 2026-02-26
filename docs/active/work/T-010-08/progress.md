# T-010-08 Progress: env-registration-and-validation

## Completed

### Step 1: Create `speednik/env_registration.py`
- Created module with three `gym.register()` calls
- Hillside-v0 (3600 steps), Pipeworks-v0 (5400), Skybridge-v0 (7200)
- Passes `max_steps` in kwargs to align with `max_episode_steps`
- No Pyxel imports

### Step 2: Add registration and validation tests to `tests/test_env.py`
- `test_registration_creates_envs` — all 3 env IDs create and reset successfully via `gym.make()`
- `test_check_env_hillside_registered` — `check_env` passes (with `skip_render_check=True`)
- `test_check_env_pipeworks_registered` — same
- `test_check_env_skybridge_registered` — same
- `test_random_actions_100_steps` — 100 steps with random actions, verifies shape/type, handles resets
- `test_observations_finite_during_random_play` — `np.isfinite` on every observation
- `test_reset_after_termination` — forces death, resets, verifies clean state
- `test_no_pyxel_import_env_registration` — guards headless safety

### Step 3: Run tests
- All 39 tests in `tests/test_env.py` pass
- Full suite: 974 passed, 5 xfailed, 0 failures

## Deviations from Plan

### Render check skipped for registered envs
When `check_env` runs on an env with a spec (created via `gym.make()`), it also validates render modes by calling `render()`. `SpeednikEnv` doesn't implement `render()` (rendering is Pyxel's job in the game, not the headless env). Used `skip_render_check=True` to avoid `NotImplementedError`. The existing direct-instantiation `test_gymnasium_env_checker` doesn't hit this because envs without a spec skip render mode testing.

## Remaining

Nothing — all acceptance criteria addressed.
