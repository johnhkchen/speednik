# T-010-05 Structure: Programmed Agents

## Files Created

### `speednik/agents/idle.py`
- `class IdleAgent` — stateless, returns ACTION_NOOP
- Imports: `from speednik.agents.actions import ACTION_NOOP`
- No numpy import needed (obs argument unused)
- ~15 lines

### `speednik/agents/hold_right.py`
- `class HoldRightAgent` — stateless, returns ACTION_RIGHT
- Imports: `from speednik.agents.actions import ACTION_RIGHT`
- ~15 lines

### `speednik/agents/jump_runner.py`
- `class JumpRunnerAgent` — stateful (tracks _was_airborne, _first_call)
- Imports: `from speednik.agents.actions import ACTION_RIGHT, ACTION_RIGHT_JUMP`
- `__init__()` sets _was_airborne=False, _first_call=True
- `act(obs)` detects landing transitions and first-frame jump
- `reset()` resets both state fields
- ~30 lines

### `speednik/agents/spindash.py`
- `class SpindashAgent` — stateful (phase, counter)
- Phase constants: CROUCH=0, CHARGE=1, RELEASE=2, RUN=3 (class-level)
- Imports: `from speednik.agents.actions import ACTION_DOWN, ACTION_DOWN_JUMP, ACTION_RIGHT`
- `__init__(charge_frames=3, redash_speed=0.125)` stores params, sets phase=CROUCH
- `act(obs)` reads obs[4] (on_ground), obs[5] (ground_speed), obs[6] (is_rolling)
- `reset()` resets phase and counter
- ~40 lines

### `speednik/agents/scripted.py`
- `class ScriptedAgent` — stateful (frame counter)
- Imports: `from speednik.agents.actions import ACTION_NOOP`
- `__init__(timeline: list[tuple[int, int, int]])` stores timeline, sets _frame=0
- `act(obs)` scans timeline for active window, increments _frame
- `reset()` resets _frame to 0
- ~25 lines

### `speednik/agents/registry.py`
- `AGENT_REGISTRY: dict[str, type]` mapping 5 names to classes
- `resolve_agent(name: str, params: dict | None = None) -> Agent` factory
- Imports all 5 agent classes
- No numpy or typing imports needed beyond `Agent` type hint
- ~25 lines

## Files Modified

### `speednik/agents/__init__.py`
- Add imports for: IdleAgent, HoldRightAgent, JumpRunnerAgent, SpindashAgent,
  ScriptedAgent, AGENT_REGISTRY, resolve_agent
- Add to `__all__` list

### `tests/test_agents.py`
- Add ~120 lines of new tests organized in sections:
  - Programmed agent protocol conformance (5 tests)
  - Behavioral correctness (5 tests)
  - Registry resolution (2 tests)
  - Smoke tests with simulation (2 tests)
  - No-Pyxel import checks (6 tests)

## Module Dependency Graph

```
speednik/agents/actions.py  ← (existing, no changes)
    ↑
    ├── speednik/agents/idle.py
    ├── speednik/agents/hold_right.py
    ├── speednik/agents/jump_runner.py
    ├── speednik/agents/spindash.py
    ├── speednik/agents/scripted.py
    │
    └── speednik/agents/registry.py
            ↑ imports all 5 agent classes
            ↑
        speednik/agents/__init__.py  ← re-exports everything
```

Tests depend on:
```
tests/test_agents.py
    ├── speednik.agents (all exports)
    ├── speednik.simulation (create_sim, sim_step)
    ├── speednik.observation (extract_observation)
    └── speednik.physics (InputState — existing)
```

## Public Interface

After implementation, `speednik.agents` exports:

```python
# Existing (unchanged)
Agent, ACTION_NOOP, ACTION_LEFT, ACTION_RIGHT, ACTION_JUMP,
ACTION_LEFT_JUMP, ACTION_RIGHT_JUMP, ACTION_DOWN, ACTION_DOWN_JUMP,
NUM_ACTIONS, ACTION_MAP, action_to_input

# New
IdleAgent, HoldRightAgent, JumpRunnerAgent, SpindashAgent, ScriptedAgent,
AGENT_REGISTRY, resolve_agent
```

## Ordering

No ordering constraints — all 5 agent files are independent. Registry depends on all
5 agents. `__init__.py` update depends on registry. Tests depend on everything.

Logical order: agents → registry → __init__ → tests.
