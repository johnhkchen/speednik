# T-010-06 Research: SpeednikEnv Core

## Scope

Build the `SpeednikEnv` Gymnasium environment class — Layer 5 of the scenario testing
architecture. Bridges the headless simulation (Layer 2) with RL training (Layer 6).

## Existing Infrastructure

### Simulation Layer (T-010-02, complete)

- **`speednik/simulation.py`** — `SimState` dataclass, `create_sim(stage_name)` factory,
  `sim_step(sim, inp) -> list[Event]` frame-advance function.
- `SimState` fields relevant to the env: `frame`, `max_x_reached`, `rings_collected`,
  `deaths`, `goal_reached`, `player_dead`, `goal_x`, `goal_y`, `level_width`, `level_height`.
- `sim_step` mutates `SimState` in place and returns event list.
- Event types: `RingCollectedEvent`, `DamageEvent`, `DeathEvent`, `SpringEvent`,
  `GoalReachedEvent`, `CheckpointEvent`.
- Death handling: once `player.state == PlayerState.DEAD`, `sim_step` sets `player_dead=True`
  once and returns `[DeathEvent()]` every subsequent call.

### Agent Interface (T-010-04, complete)

- **`speednik/agents/actions.py`** — `NUM_ACTIONS = 8`, `ACTION_MAP` (int → InputState
  template), `action_to_input(action, prev_jump_held) -> (InputState, bool)`.
- `action_to_input` handles jump edge detection: `jump_pressed = jump_in_action and not
  prev_jump_held`. Caller stores returned bool for next frame.

### Observation (T-010-04, complete)

- **`speednik/observation.py`** — `OBS_DIM = 12`, `extract_observation(sim) -> np.ndarray`.
- 12-dim flat float32 vector: position (2), velocity (2), on_ground, ground_speed,
  is_rolling, facing_right, angle, max_progress, distance_to_goal, time_fraction.
- All values normalized; suitable for Box observation space.

### Physics Input (no Pyxel dependency)

- **`speednik/physics.py`** — `InputState` dataclass with `left`, `right`, `jump_pressed`,
  `jump_held`, `down_held`, `up_held` booleans.

## Dependencies Check

- `gymnasium` is NOT in `pyproject.toml` yet. Needs `uv add gymnasium`.
- `numpy` is already a dependency.
- No Pyxel imports allowed in env.py (headless constraint).

## Spec Reference

`docs/specs/scenario-testing-system.md` §3.1 defines the class structure, §3.2 defines
reward (deferred to T-010-07), §3.4 defines Gymnasium registration (separate concern, not
in this ticket).

## Key Design Points from Spec

1. **Flat Box observation space** — CleanRL's ppo.py expects simple shape tuple, not Dict.
2. **Discrete(8) action space** — 8 actions matching ACTION_MAP.
3. **`_action_to_input` uses env-internal `_prev_jump_held`** — mirrors `action_to_input()`
   from actions.py but uses instance state rather than caller-managed state.
4. **Reward placeholder** — ticket says "return 0.0 until T-010-07 implements it".
5. **`_get_info`** — dict with frame, x, y, max_x, rings, deaths, goal_reached.
6. **`terminated`** — `goal_reached or player_dead`.
7. **`truncated`** — `step_count >= max_steps`.

## Test Patterns in Codebase

- Tests import from `speednik.*`, use `create_sim("hillside")`, check shapes/dtypes.
- No fixtures; each test creates its own state.
- `_make_obs()` helper pattern for building synthetic observations.
- Source-level no-Pyxel assertions via `inspect.getfile`.
- Smoke tests: run agent for N frames, assert meaningful outcome.

## Constraints

- Must subclass `gymnasium.Env` (not `gym.Env` from old API).
- Must follow Gymnasium v1.0 API: `reset()` returns `(obs, info)`, `step()` returns
  `(obs, reward, terminated, truncated, info)`.
- `render_mode` accepted but rendering not implemented in this ticket.
- `sim` starts as `None`, initialized on first `reset()`.
- Multiple `reset()` calls must work (create fresh sim each time).

## Existing File: None

`speednik/env.py` does not exist yet — this is a new file.
