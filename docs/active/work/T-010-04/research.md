# T-010-04 Research: Agent Protocol and Observation Extraction

## Scope

This ticket covers Layer 3 of the architecture: the `Agent` protocol, the action
space (8 discrete actions mapping to `InputState`), the `action_to_input` helper
with jump edge detection, and the `extract_observation` function (12-dim simplified
vector). Four files to create:

- `speednik/agents/__init__.py`
- `speednik/agents/base.py`
- `speednik/agents/actions.py`
- `speednik/observation.py`

## Existing Types and Interfaces

### InputState (`speednik/physics.py:67-74`)

```python
@dataclass
class InputState:
    left: bool = False
    right: bool = False
    jump_pressed: bool = False
    jump_held: bool = False
    down_held: bool = False
    up_held: bool = False
```

Key subtlety: `jump_pressed` fires a jump initiation (one frame), `jump_held`
sustains the jump (variable height). The caller must track previous frame's
jump state to set `jump_pressed` only on the rising edge.

### PhysicsState (`speednik/physics.py:77-91`)

All 12 observation inputs come from this plus SimState fields:

| Field | Type | Range | Observation use |
|-------|------|-------|-----------------|
| `x` | float | 0..level_width | obs[0] normalized |
| `y` | float | 0..level_height | obs[1] normalized |
| `x_vel` | float | [-16, 16] | obs[2] / MAX_X_SPEED |
| `y_vel` | float | unbounded (gravity) | obs[3] / MAX_X_SPEED |
| `ground_speed` | float | [-16, 16] | obs[5] / MAX_X_SPEED |
| `on_ground` | bool | 0/1 | obs[4] float cast |
| `is_rolling` | bool | 0/1 | obs[6] float cast |
| `facing_right` | bool | 0/1 | obs[7] float cast |
| `angle` | int | 0-255 | obs[8] / 255.0 |

### SimState (`speednik/simulation.py:91-113`)

Additional observation fields:

| Field | Type | Observation use |
|-------|------|-----------------|
| `max_x_reached` | float | obs[9] / level_width |
| `goal_x` | float | obs[10] = (goal_x - p.x) / level_width |
| `level_width` | int | normalization divisor |
| `level_height` | int | normalization divisor |
| `frame` | int | obs[11] / 3600.0 |

### Constants (`speednik/constants.py`)

- `MAX_X_SPEED = 16.0` — used for velocity normalization
- No existing constant for default episode length (3600 is the spec default)

### Player (`speednik/player.py:74-92`)

The `Player` dataclass wraps `PhysicsState` at `player.physics`. The observation
function accesses `sim.player.physics` for kinematics and `sim` directly for
progress metrics.

### Existing sim_step interface

`sim_step(sim: SimState, inp: InputState) -> list[Event]` — the caller converts
an action int to InputState before calling. The `action_to_input` function goes
between the agent's discrete output and this interface.

## Jump Edge Detection Pattern

The spec (§3.1) and env design (§3.2) establish that `jump_pressed` should be
True only on the first frame of a jump action. The pattern:

```python
jump_in_action = ACTION_MAP[action].jump_pressed
inp = InputState(
    ...,
    jump_pressed=jump_in_action and not prev_jump_held,
    jump_held=jump_in_action,
    ...
)
new_prev_jump_held = jump_in_action
```

The caller owns `prev_jump_held` state. The `action_to_input` function returns
both the InputState and the updated `prev_jump_held` flag.

## Dependency: numpy

numpy is NOT currently a project dependency. The ticket requires `np.ndarray` for
observations and `np.zeros`/`np.float32` for construction. Must be added to
`pyproject.toml` dependencies.

## Dependency: T-010-02 (sim_step)

T-010-02 is phase:done. The working tree has unstaged changes that add `sim_step`
to `simulation.py`. This ticket depends on SimState and its fields being available,
which they are from the committed T-010-01 code. The observation function reads
SimState fields but does not call sim_step.

## Test Infrastructure

Existing test pattern: pure pytest, no fixtures beyond what's in `tests/grids.py`
and `tests/harness.py`. Tests import directly from modules. The `create_sim`
factory provides real stage data for integration-style tests.

Test command: `uv run pytest tests/ -x` (per acceptance criteria).

## Constraints

1. **No Pyxel imports** — acceptance criterion, consistent with Layer 2+.
2. **Protocol, not ABC** — `@runtime_checkable` for `isinstance` checks.
3. **12-dim simplified obs** — raycasts deferred to T-010-16/17.
4. **Normalization to ~[-1, 1]** — velocities by MAX_X_SPEED, positions by level
   dims, angle by 255, booleans as 0.0/1.0.
5. **numpy float32** — CleanRL/Gymnasium compatibility.

## Codebase Patterns

- All game logic modules use `from __future__ import annotations`.
- Dataclasses preferred over NamedTuples.
- Type unions use `X | Y` syntax (Python 3.10+).
- Constants are module-level ALL_CAPS in `constants.py`.
- No `__all__` exports; direct imports throughout.
