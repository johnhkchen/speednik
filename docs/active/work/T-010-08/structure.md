# T-010-08 Structure: env-registration-and-validation

## Files Created

### `speednik/env_registration.py`

New module. Module-level code only — no classes or functions.

```
Imports:
  - gymnasium as gym

Top-level calls:
  - gym.register("speednik/Hillside-v0", ...)
  - gym.register("speednik/Pipeworks-v0", ...)
  - gym.register("speednik/Skybridge-v0", ...)
```

Each registration specifies:
- `id`: Gymnasium namespace format `speednik/<Stage>-v0`
- `entry_point`: `"speednik.env:SpeednikEnv"`
- `kwargs`: `{"stage": "<stage_name>", "max_steps": <N>}`
- `max_episode_steps`: matches `max_steps` value

Stage configurations:
| Stage     | max_steps | max_episode_steps |
|-----------|-----------|-------------------|
| hillside  | 3600      | 3600              |
| pipeworks | 5400      | 5400              |
| skybridge | 7200      | 7200              |

No Pyxel imports. No imports from speednik.env (entry_point is a string reference).

## Files Modified

### `tests/test_env.py`

Append new test sections after existing tests. All new tests are self-contained.

New test sections:

#### Registration section

```
test_registration_creates_envs()
  - import speednik.env_registration
  - gym.make("speednik/Hillside-v0")  → creates successfully
  - gym.make("speednik/Pipeworks-v0") → creates successfully
  - gym.make("speednik/Skybridge-v0") → creates successfully
```

#### check_env via registry section

```
test_check_env_hillside_registered()
  - env = gym.make("speednik/Hillside-v0")
  - check_env(env.unwrapped)

test_check_env_pipeworks_registered()
  - same pattern for pipeworks

test_check_env_skybridge_registered()
  - same pattern for skybridge
```

#### Random action loop section

```
test_random_actions_100_steps()
  - SpeednikEnv(stage="hillside")
  - reset, 100 steps of random actions
  - assert obs shape, reward type
  - reset on termination/truncation
```

#### Finite observations section

```
test_observations_finite_during_random_play()
  - 100 random steps
  - np.all(np.isfinite(obs)) on every step
```

#### Reset after termination section

```
test_reset_after_termination()
  - Force death, step to get terminated
  - reset(), verify clean state
```

#### No-Pyxel guard for registration module

```
test_no_pyxel_import_env_registration()
  - Read source of env_registration.py
  - Assert no "import pyxel" or "from pyxel"
```

## Files Unchanged

- `speednik/env.py` — no modifications needed
- `speednik/observation.py` — no modifications needed
- `speednik/simulation.py` — no modifications needed
- `pyproject.toml` — gymnasium already a dependency

## Module Boundaries

- `env_registration.py` depends only on `gymnasium` (string-based entry_point)
- Tests depend on `speednik.env_registration` (for `gym.make`) and `speednik.env` (for direct instantiation)
- No circular dependencies introduced

## Ordering

1. Create `speednik/env_registration.py` (no dependencies on other new code)
2. Add tests to `tests/test_env.py` (depends on step 1)
3. Run full test suite to verify no regressions
