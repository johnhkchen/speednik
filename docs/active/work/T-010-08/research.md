# T-010-08 Research: env-registration-and-validation

## Objective

Register SpeednikEnv with Gymnasium's env registry for three stages (Hillside, Pipeworks, Skybridge) and validate with `check_env` and random-action loop tests.

## Current Codebase State

### SpeednikEnv (`speednik/env.py`)

Fully implemented Gymnasium environment. Key surface:

- **observation_space:** `Box(-inf, inf, shape=(12,), float32)`
- **action_space:** `Discrete(8)`
- **Constructor:** `SpeednikEnv(stage="hillside", render_mode=None, max_steps=3600)`
- **reset():** Creates fresh `SimState` via `create_sim(stage_name)`, returns `(obs, info)`
- **step(action):** Delegates to `sim_step`, returns 5-tuple `(obs, reward, terminated, truncated, info)`
- **Termination:** `goal_reached` or `player_dead` → `terminated=True`
- **Truncation:** `_step_count >= max_steps` → `truncated=True`

No Pyxel imports — safe for headless operation.

### Simulation (`speednik/simulation.py`)

- `create_sim(stage_name)` → `SimState` — loads tile/entity data from JSON stage files
- `sim_step(sim, inp)` → `list[Event]` — deterministic frame advance
- Supports three stages: `hillside`, `pipeworks`, `skybridge`
- Performance: ~20k–50k updates/sec headless

### Observation (`speednik/observation.py`)

- `OBS_DIM = 12` — flat float32 vector
- `extract_observation(sim)` → normalized kinematics, state flags, progress metrics

### Actions (`speednik/agents/actions.py`)

- `NUM_ACTIONS = 8` — noop, left, right, jump, left+jump, right+jump, down, down+jump
- `action_to_input(action, prev_jump_held)` → `(InputState, bool)` — jump edge detection

### Dependencies (`pyproject.toml`)

- `gymnasium>=1.2.3` already in project dependencies
- `numpy`, `pyyaml` also present
- `pytest>=9.0.2` in dev dependencies

### Existing Tests (`tests/test_env.py`)

31 tests covering:
- Space definitions, reset, step mechanics
- Jump edge detection
- Termination (goal, death, max_steps)
- Reward computation (idle, hold-right, goal, death, ring, time penalty)
- Multiple episodes, state reset
- `check_env` on direct `SpeednikEnv()` instantiation
- All three stages
- No-Pyxel-import guard

**Key gap:** Tests use direct instantiation `SpeednikEnv()`, never `gym.make()`. No `env_registration.py` exists.

### Package Init (`speednik/__init__.py`)

Empty file. Could be used for registration, but ticket specifies a separate module.

### Spec Reference (`docs/specs/scenario-testing-system.md` §3.4)

Specifies three registrations:
- `speednik/Hillside-v0` → `stage="hillside"`, `max_episode_steps=3600`
- `speednik/Pipeworks-v0` → `stage="pipeworks"`, `max_episode_steps=5400`
- `speednik/Skybridge-v0` → `stage="skybridge"`, `max_episode_steps=7200`

Entry point: `speednik.env:SpeednikEnv`. Registration via `gym.register()`.

## Gymnasium Registration Mechanics

- `gym.register(id, entry_point, kwargs, max_episode_steps)` adds to the global registry
- `gym.make(id)` creates an env wrapped in `TimeLimit` (handles truncation via `max_episode_steps`)
- Registration is idempotent if the same ID/entry_point/kwargs are used
- `check_env(env.unwrapped)` validates the raw env (no wrappers)
- The `env.unwrapped` is needed because `TimeLimit` wrapper adds its own truncation

## Constraints and Risks

1. **Double truncation:** `SpeednikEnv.max_steps` defaults to 3600, but `gym.make` wraps in `TimeLimit(max_episode_steps=N)`. Both can truncate. When using `gym.make`, the `TimeLimit` wrapper handles truncation. The `max_steps` param in `SpeednikEnv.__init__` should be set high enough to not interfere, or rely on the wrapper.

2. **Observation bounds:** `check_env` warns (not errors) about infinite observation bounds. Existing test already passes with this warning.

3. **Stage loading:** Each `create_sim(stage)` loads JSON data from disk. Tests must have access to stage data files.

4. **Import side effects:** `import speednik.env_registration` triggers `gym.register()` calls. This is the standard pattern — CleanRL and scenario runner will import this module.

## Files to Create

- `speednik/env_registration.py` — three `gym.register()` calls
- Tests in `tests/test_env.py` (extend existing) — registration + `gym.make` + `check_env` via registry + random loop

## Files to Modify

- `tests/test_env.py` — add registration and validation tests
