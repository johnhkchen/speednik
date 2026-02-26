# T-010-04 Structure: Agent Protocol and Observation Extraction

## Files Created

### `speednik/agents/__init__.py`

Package init. Re-exports the public API for convenience:

```
from speednik.agents.base import Agent
from speednik.agents.actions import (
    ACTION_NOOP, ACTION_LEFT, ACTION_RIGHT, ACTION_JUMP,
    ACTION_LEFT_JUMP, ACTION_RIGHT_JUMP, ACTION_DOWN, ACTION_DOWN_JUMP,
    NUM_ACTIONS, ACTION_MAP, action_to_input,
)
```

### `speednik/agents/base.py`

Single responsibility: the Agent protocol.

Public interface:
- `Agent` — `@runtime_checkable` Protocol with `act(obs: np.ndarray) -> int`
  and `reset() -> None`

Imports: `typing.Protocol`, `typing.runtime_checkable`, `numpy`

No other classes, no constants, no helpers. Minimal file.

### `speednik/agents/actions.py`

Action space constants and the input mapping helper.

Public interface:
- `ACTION_NOOP = 0` through `ACTION_DOWN_JUMP = 7`
- `NUM_ACTIONS = 8`
- `ACTION_MAP: dict[int, InputState]` — maps action int to template InputState
- `action_to_input(action: int, prev_jump_held: bool) -> tuple[InputState, bool]`

Imports: `speednik.physics.InputState`

The `action_to_input` function:
1. Looks up the base InputState template from ACTION_MAP
2. Determines if this action involves jumping (`base.jump_held`)
3. Sets `jump_pressed = jump_in_action and not prev_jump_held`
4. Returns `(new_InputState, jump_in_action)` — the second element becomes
   the caller's new `prev_jump_held`

### `speednik/observation.py`

Observation extraction from SimState.

Public interface:
- `OBS_DIM = 12`
- `extract_observation(sim: SimState) -> np.ndarray`

Imports: `numpy`, `speednik.simulation.SimState`, `speednik.constants.MAX_X_SPEED`

The function reads SimState fields (player.physics for kinematics, sim-level for
progress) and returns a flat float32 vector. No mutation of sim.

Observation layout:

| Index | Name | Source | Normalization |
|-------|------|--------|---------------|
| 0 | x_pos | p.x | / level_width |
| 1 | y_pos | p.y | / level_height |
| 2 | x_vel | p.x_vel | / MAX_X_SPEED |
| 3 | y_vel | p.y_vel | / MAX_X_SPEED |
| 4 | on_ground | p.on_ground | float() |
| 5 | ground_speed | p.ground_speed | / MAX_X_SPEED |
| 6 | is_rolling | p.is_rolling | float() |
| 7 | facing_right | p.facing_right | float() |
| 8 | angle | p.angle | / 255.0 |
| 9 | max_progress | sim.max_x_reached | / level_width |
| 10 | dist_to_goal | goal_x - p.x | / level_width |
| 11 | time_frac | sim.frame | / 3600.0 |

## Files Modified

### `pyproject.toml`

Add `numpy` to `[project.dependencies]`:

```toml
dependencies = ["pyxel", "numpy"]
```

## Files NOT Modified

- `speednik/simulation.py` — no changes needed, observation reads existing fields
- `speednik/constants.py` — MAX_X_SPEED already exists, no new constants needed
- `speednik/physics.py` — InputState already exists, no changes needed

## Test Files Created

### `tests/test_agents.py`

Tests for the Agent protocol and action space:

1. Protocol conformance — verify a minimal class satisfies `isinstance(obj, Agent)`
2. Protocol rejection — verify a class missing `act` fails isinstance
3. Action constants — verify 8 actions, 0-7, all unique
4. ACTION_MAP completeness — all 8 actions present, values are InputState
5. ACTION_MAP correctness — spot-check specific mappings (NOOP has no flags,
   RIGHT has right=True, JUMP has jump_pressed + jump_held, etc.)
6. action_to_input basic — NOOP returns all-False InputState
7. action_to_input jump edge detection — first jump frame has jump_pressed=True,
   second frame has jump_pressed=False, jump_held=True
8. action_to_input jump release — jump then noop resets prev_jump_held
9. action_to_input directional + jump combos — LEFT_JUMP, RIGHT_JUMP, DOWN_JUMP
10. NUM_ACTIONS matches ACTION_MAP size

### `tests/test_observation.py`

Tests for observation extraction:

1. Output shape — 12 elements, float32 dtype
2. Normalization bounds — on a fresh sim, check positions in [0, 1], velocities
   near 0, booleans are 0.0 or 1.0
3. Position normalization — known x,y produce expected obs[0], obs[1]
4. Velocity normalization — set x_vel to MAX_X_SPEED, verify obs[2] == 1.0
5. Boolean encoding — on_ground=True -> 1.0, is_rolling=False -> 0.0
6. Angle normalization — angle=128 -> obs[8] ≈ 0.502
7. Progress tracking — set max_x_reached, verify obs[9]
8. Distance to goal — verify obs[10] = (goal_x - x) / level_width
9. Time fraction — set frame=1800, verify obs[11] = 0.5
10. No Pyxel import in observation.py
11. No Pyxel import in agents/base.py
12. No Pyxel import in agents/actions.py
13. After sim_step, observation reflects updated state

## Module Dependency Graph

```
speednik/agents/base.py
  └── numpy

speednik/agents/actions.py
  └── speednik.physics (InputState)

speednik/agents/__init__.py
  ├── speednik.agents.base (Agent)
  └── speednik.agents.actions (constants, action_to_input)

speednik/observation.py
  ├── numpy
  ├── speednik.simulation (SimState)
  └── speednik.constants (MAX_X_SPEED)
```

No circular dependencies. No upward layer violations. observation.py bridges
Layer 2 (simulation) and Layer 3 (agents) without either depending on the other.
