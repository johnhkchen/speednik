# T-010-05 Design: Programmed Agents

## Decision Summary

Each agent is a concrete class in its own module. All conform to the `Agent` protocol
via duck typing (no inheritance). A flat registry dict maps string names to classes.

---

## Approach: One Class Per Module

**Chosen.** Each agent lives in its own file under `speednik/agents/`. This matches
the ticket specification exactly and keeps each agent self-contained.

**Rejected alternative: all agents in a single file.** Would be simpler but harder to
navigate as agents grow more complex. The one-file-per-agent pattern also aligns with
the spec §4.2 which shows separate file headers.

---

## Agent Designs

### IdleAgent (`idle.py`)

Stateless. `act()` returns `ACTION_NOOP`. `reset()` is a no-op. No constructor args.

### HoldRightAgent (`hold_right.py`)

Stateless. `act()` returns `ACTION_RIGHT`. `reset()` is a no-op. No constructor args.

### JumpRunnerAgent (`jump_runner.py`)

**Design decision: landing-based jumps (no raycasts)**

The spec §4.2 uses `obs[18]` (forward ray distance) which doesn't exist in the current
12-dim observation. The ticket explicitly says: "Initial version without raycasts can
jump periodically or when on_ground transitions from False→True."

Strategy: run right, jump on first frame, re-jump after every landing. This matches
the harness `hold_right_jump()` behavior.

State: `_was_airborne: bool` — tracks whether the previous frame was in the air.

Logic:
```
on_ground = obs[4] > 0.5
just_landed = _was_airborne and on_ground
_was_airborne = not on_ground
if first_call or just_landed: return ACTION_RIGHT_JUMP
else: return ACTION_RIGHT
```

The `_first_call` flag ensures the agent jumps on the very first frame when grounded
(matching harness behavior of pressing jump on frame 0).

`reset()` resets `_was_airborne` and `_first_call`.

**Rejected: timer-based jumping.** Periodic jumps (every N frames) are less responsive
and don't match the harness behavior. Landing detection is more Sonic-like.

**Rejected: velocity-drop detection.** Checking x_vel drops could indicate obstacles
but is unreliable on slopes. Landing detection is simpler and more predictable.

### SpindashAgent (`spindash.py`)

State machine with 4 phases: CROUCH → CHARGE → RELEASE → RUN.

Constructor params:
- `charge_frames: int = 3` — number of frames to hold CHARGE
- `redash_speed: float = 0.125` — normalized ground_speed threshold for re-dashing

**Design decision: normalized threshold default**

The harness uses `redash_threshold=2.0` in raw physics units. Normalized:
`2.0 / MAX_X_SPEED = 2.0 / 16.0 = 0.125`. Using normalized units because that's
what the observation provides.

**Design decision: is_rolling as SPINDASH proxy**

The harness checks `player.state != PlayerState.SPINDASH` to avoid re-dashing during
an active spindash. The observation doesn't expose PlayerState. Instead, use
`obs[6] > 0.5` (is_rolling) as a proxy — during active spindash the player is rolling.

Re-dash condition: `on_ground AND |ground_speed| < threshold AND NOT is_rolling`

This may differ slightly from the harness on terrain that induces rolling (e.g. steep
downhills), but those cases are rare in practice and the ticket says "similar (not
identical) behavior" is expected.

Phase logic:
- CROUCH: return ACTION_DOWN, advance to CHARGE, reset counter
- CHARGE: return ACTION_DOWN_JUMP, increment counter. When counter >= charge_frames,
  advance to RELEASE
- RELEASE: return ACTION_RIGHT, advance to RUN
- RUN: return ACTION_RIGHT. If re-dash condition met, go to CROUCH

`reset()` resets phase to CROUCH and counter to 0.

### ScriptedAgent (`scripted.py`)

Takes a timeline of `(start_frame, end_frame, action_int)` tuples. Maintains an
internal frame counter incremented on each `act()` call.

**Design decision: action ints, not InputState**

The harness scripted strategy uses InputState tuples. The agent interface returns
action ints. The timeline uses action ints for consistency with the agent protocol.

Constructor: `timeline: list[tuple[int, int, int]]`

Logic:
```
for (start, end, action) in timeline:
    if start <= self._frame < end:
        self._frame += 1
        return action
self._frame += 1
return ACTION_NOOP  # default when no window matches
```

`reset()` resets `_frame` to 0.

---

## Registry (`registry.py`)

A flat dict mapping agent name strings to classes:

```python
AGENT_REGISTRY: dict[str, type] = {
    "idle": IdleAgent,
    "hold_right": HoldRightAgent,
    "jump_runner": JumpRunnerAgent,
    "spindash": SpindashAgent,
    "scripted": ScriptedAgent,
}
```

`resolve_agent(name, params=None)` looks up the class and instantiates with kwargs.

**Error handling:** `KeyError` propagates naturally if name is unknown. No custom
exception class needed — the caller gets a clear error.

---

## Package Init Updates

`speednik/agents/__init__.py` will re-export all 5 agent classes plus the registry
function for clean imports:

```python
from speednik.agents.registry import AGENT_REGISTRY, resolve_agent
```

---

## Testing Design

### Protocol conformance (5 tests)
Each agent: instantiate, assert `isinstance(agent, Agent)`.

### Behavioral correctness (5 tests)
- IdleAgent: always returns ACTION_NOOP
- HoldRightAgent: always returns ACTION_RIGHT
- JumpRunnerAgent: returns RIGHT or RIGHT_JUMP, never other actions
- SpindashAgent: verify phase transitions (CROUCH→CHARGE→RELEASE→RUN)
- ScriptedAgent: verify timeline playback and frame counter

### Registry (2 tests)
- `resolve_agent("hold_right")` → HoldRightAgent instance
- `resolve_agent("spindash", {"charge_frames": 5})` → SpindashAgent with custom param

### Smoke tests (2 tests)
- HoldRight on hillside for 300 frames: x increases
- Spindash on hillside for 300 frames: reaches higher x than HoldRight

### No-Pyxel checks (6 tests)
One per module (idle, hold_right, jump_runner, spindash, scripted, registry).
