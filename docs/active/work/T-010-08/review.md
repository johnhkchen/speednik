# T-010-08 Review: env-registration-and-validation

## Summary of Changes

### Files Created

- **`speednik/env_registration.py`** — Registers three Gymnasium environments:
  - `speednik/Hillside-v0` (stage=hillside, 3600 max steps)
  - `speednik/Pipeworks-v0` (stage=pipeworks, 5400 max steps)
  - `speednik/Skybridge-v0` (stage=skybridge, 7200 max steps)
  - Import triggers registration: `import speednik.env_registration`
  - No Pyxel imports — safe for headless use

### Files Modified

- **`tests/test_env.py`** — Added 8 new tests (31 → 39 total):
  - `test_registration_creates_envs` — `gym.make()` works for all 3 env IDs
  - `test_check_env_hillside_registered` — Gymnasium validator passes
  - `test_check_env_pipeworks_registered` — Gymnasium validator passes
  - `test_check_env_skybridge_registered` — Gymnasium validator passes
  - `test_random_actions_100_steps` — 100-step stability under random input
  - `test_observations_finite_during_random_play` — no NaN/Inf values
  - `test_reset_after_termination` — clean recovery after episode end
  - `test_no_pyxel_import_env_registration` — headless import guard

### Files Unchanged

- `speednik/env.py` — no changes needed
- `pyproject.toml` — `gymnasium>=1.2.3` was already a dependency

## Acceptance Criteria Coverage

| Criterion | Status | Test |
|-----------|--------|------|
| gymnasium added as dependency | Already present | — |
| Three envs registered | Done | `test_registration_creates_envs` |
| `gym.make("speednik/Hillside-v0")` works | Done | `test_registration_creates_envs` |
| `check_env` passes for Hillside-v0 | Done | `test_check_env_hillside_registered` |
| `check_env` passes for Pipeworks-v0 | Done | `test_check_env_pipeworks_registered` |
| `check_env` passes for Skybridge-v0 | Done | `test_check_env_skybridge_registered` |
| 100-step random action loop | Done | `test_random_actions_100_steps` |
| Reset after termination | Done | `test_reset_after_termination` |
| Observations finite (no NaN/Inf) | Done | `test_observations_finite_during_random_play` |
| No Pyxel imports in env_registration.py | Done | `test_no_pyxel_import_env_registration` |
| `uv run pytest tests/test_env.py -x` passes | Done | 39/39 pass |

## Test Coverage

- **39 tests** in `tests/test_env.py` — all passing
- **974 tests** across the full suite — all passing (5 xfailed)
- Gymnasium's `check_env` validates observation/action space conformance, reset/step return types, and observation bounds for all 3 stages
- Random action loop validates stability under diverse input sequences
- Finite-observation check guards against NaN/Inf propagation

## Open Concerns

1. **Observation bounds warning:** Gymnasium emits `UserWarning` about `-inf`/`inf` observation space bounds. This is cosmetic — `check_env` still passes. A future ticket (observation normalization or bounded observation space) could address this.

2. **Render not implemented:** `SpeednikEnv` declares `render_modes: ["human", "rgb_array"]` in metadata but doesn't implement `render()`. The `check_env` calls use `skip_render_check=True` to work around this. If RL visualization is needed later, `render()` should return an RGB array from simulation state. This is outside the scope of T-010-08.

3. **Double truncation alignment:** `max_steps` is passed in kwargs to match `max_episode_steps`, so both the inner env and the `TimeLimit` wrapper agree on when to truncate. If someone instantiates `SpeednikEnv()` directly without passing `max_steps`, it defaults to 3600 regardless of stage — this is fine for direct use but worth noting.

## Conclusion

Small, focused change: one new 30-line module and 8 new tests. All acceptance criteria met. The environments are now discoverable via Gymnasium's standard `gym.make()` interface, validated by `check_env`, and stable under random input.
