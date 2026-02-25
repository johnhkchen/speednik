# T-010-06 Structure: SpeednikEnv Core

## Files Created

### `speednik/env.py` (new)

The core Gymnasium environment class.

**Imports:**
- `gymnasium` (gym.Env, spaces)
- `numpy`
- `speednik.simulation` (SimState, create_sim, sim_step)
- `speednik.observation` (OBS_DIM, extract_observation)
- `speednik.agents.actions` (NUM_ACTIONS, action_to_input)

**Class: `SpeednikEnv(gym.Env)`**

Class attributes:
- `metadata`: dict with render_modes and render_fps

Instance attributes (set in `__init__`):
- `stage_name: str`
- `render_mode: str | None`
- `max_steps: int`
- `observation_space: spaces.Box`
- `action_space: spaces.Discrete`
- `sim: SimState | None`
- `_step_count: int`
- `_prev_jump_held: bool`

Public methods:
- `reset(*, seed=None, options=None) -> tuple[np.ndarray, dict]`
- `step(action: int) -> tuple[np.ndarray, float, bool, bool, dict]`

Private methods:
- `_action_to_input(action: int) -> InputState`
- `_get_obs() -> np.ndarray`
- `_compute_reward(events: list) -> float`
- `_get_info() -> dict`

### `tests/test_env.py` (new)

Test file for SpeednikEnv.

**Test groups:**

1. **Space definitions** — observation_space shape/dtype, action_space.n
2. **Reset** — returns (obs, info), obs shape matches, info keys present
3. **Step** — returns 5-tuple, obs shape, reward is float, terminated/truncated are bool
4. **Action-to-input / jump edge detection** — via stepping with jump actions
5. **Termination: goal reached** — manipulate sim.goal_x to trigger
6. **Termination: player dead** — manipulate sim.player_dead to trigger
7. **Truncation: max_steps** — step until truncated
8. **Info dict** — all expected keys, sensible values
9. **Multiple episodes** — reset/step/reset/step works cleanly
10. **Gymnasium env_checker** — `check_env(env)` passes
11. **No Pyxel imports** — source-level check

## Files Modified

### `pyproject.toml`

Add `gymnasium` to the `dependencies` list.

## Files Unchanged

- `speednik/simulation.py` — used as-is
- `speednik/observation.py` — used as-is
- `speednik/agents/actions.py` — used as-is
- `speednik/physics.py` — InputState used as-is

## Module Boundaries

SpeednikEnv is a pure adapter. It:
- Creates simulation state via `create_sim()`
- Advances it via `sim_step()`
- Extracts observations via `extract_observation()`
- Maps actions via `action_to_input()`
- Manages Gymnasium lifecycle (spaces, reset, step, termination, info)

No simulation logic, observation logic, or action logic lives in env.py.
Reward is a placeholder (returns 0.0) — T-010-07 will implement it.

## Dependency Direction

```
env.py  →  simulation.py
        →  observation.py
        →  agents/actions.py
```

No reverse dependencies. No circular imports.
