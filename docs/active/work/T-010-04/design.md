# T-010-04 Design: Agent Protocol and Observation Extraction

## Decision 1: Agent Protocol Shape

### Option A: Protocol with `act` + `reset` (Chosen)

```python
@runtime_checkable
class Agent(Protocol):
    def act(self, obs: np.ndarray) -> int: ...
    def reset(self) -> None: ...
```

Duck typing — agents don't inherit, just match the signature. `isinstance(obj, Agent)`
works at runtime via `@runtime_checkable`. Matches the spec §4.1 exactly.

### Option B: ABC with abstract methods

Rejected. Forces inheritance, heavier coupling, no benefit for this use case. The
protocol approach is explicitly called out in the spec and ticket.

### Option C: Callable protocol (just `__call__`)

Rejected. Loses `reset()` semantics. Stateful agents (spindash, RL) need a way to
clear internal state between episodes.

**Rationale**: Protocol is the clear winner — it's what the spec prescribes, it
allows any class with matching methods to be used, and it's the standard Python
pattern for structural subtyping.

## Decision 2: Action Constants Location

### Option A: `speednik/agents/actions.py` (Chosen)

Dedicated module for action constants, `ACTION_MAP`, and `action_to_input`. Keeps
the agents package self-contained for its domain: "anything about how agents
interact with the simulation."

### Option B: Constants in `speednik/constants.py`

Rejected. `constants.py` holds physics/game constants. Action space is an agent
interface concern, not a physics concern. Mixing them muddies the layering.

### Option C: Constants in `speednik/agents/base.py`

Rejected. `base.py` defines the protocol; actions are a separate concern. An agent
doesn't need to know about action constants to conform to the protocol — it just
returns an int.

**Rationale**: Clean separation. `base.py` = protocol, `actions.py` = action space
and input mapping. Both live in `speednik/agents/` since they're Layer 3 concerns.

## Decision 3: `action_to_input` Return Type

### Option A: Return `tuple[InputState, bool]` (Chosen)

```python
def action_to_input(action: int, prev_jump_held: bool) -> tuple[InputState, bool]:
```

Returns `(input_state, new_prev_jump_held)`. The caller manages state. This is a
pure function — no hidden state, easy to test, matches the ticket's specification.

### Option B: Stateful converter class

Rejected. Unnecessary complexity. The state is a single boolean. A class that wraps
one boolean is over-engineering.

### Option C: Return only InputState, caller manages edge detection

Rejected. The edge detection logic is fiddly (must check `jump_pressed` in the
base mapping, compare to previous frame). Centralizing it in `action_to_input`
prevents bugs when multiple callers need the same logic.

**Rationale**: Tuple return keeps the function pure while encapsulating the edge
detection logic. The env, scenario runner, and any future caller all benefit.

## Decision 4: Observation Function Location

### Option A: `speednik/observation.py` (Chosen)

Top-level module, not inside `agents/`. The observation function reads SimState
(Layer 2) and produces data for agents (Layer 3). It sits between the two layers.
Both the Gymnasium wrapper (Layer 5) and the scenario runner (Layer 4) will also
call it. Placing it at the package root makes it accessible without circular imports.

### Option B: `speednik/agents/observation.py`

Rejected. The function depends on SimState (Layer 2) and is consumed by the env
(Layer 5) and runner (Layer 4). Putting it in `agents/` creates a confusing
dependency direction — higher layers import from a peer package.

### Option C: Method on SimState

Rejected. Adds numpy dependency to `simulation.py`. Violates single responsibility.
SimState is a data container; observation extraction is a separate concern.

**Rationale**: `speednik/observation.py` is the cleanest layering. It imports from
Layer 2 (simulation, constants) and exports to Layer 3+ (agents, env, runner).

## Decision 5: numpy Dependency

numpy must be added to `pyproject.toml` dependencies. It's required for the
observation vector (`np.ndarray`, `np.zeros`, `np.float32`).

Adding to main `[project.dependencies]` rather than optional because every
downstream consumer (env, runner, agents) needs it. It's a core dependency for
the scenario testing system.

## Decision 6: Observation Normalization

Follow the ticket specification exactly:

- Positions: divide by `level_width` / `level_height` → [0, 1]
- Velocities: divide by `MAX_X_SPEED` (16.0) → roughly [-1, 1]
- Booleans: `float()` cast → {0.0, 1.0}
- Angle: divide by 255.0 → [0, 1]
- Progress: `max_x_reached / level_width` → [0, 1]
- Distance to goal: `(goal_x - x) / level_width` → roughly [-1, 1]
- Time: `frame / 3600.0` → [0, 1] at default episode length

`y_vel` is normalized by `MAX_X_SPEED` (not a separate MAX_Y constant) per the
spec. This means it can exceed [-1, 1] during fast falls, but that's acceptable —
the spec says "roughly" normalized, and CleanRL normalizes observations anyway.

## Decision 7: ACTION_MAP Construction

Build `ACTION_MAP` from fresh `InputState` instances, not references to mutable
singletons. Each entry is a template — `action_to_input` reads fields from the
template but constructs a new `InputState` with edge-detected `jump_pressed`.

The map uses `jump_pressed=True, jump_held=True` for jump actions in the template.
The actual `jump_pressed` flag is overridden by edge detection in `action_to_input`.

## Rejected: OBS_DIM as a constant in constants.py

The observation dimension (12) is specific to the observation module, not a physics
constant. Define `OBS_DIM` in `observation.py` where it's used.
