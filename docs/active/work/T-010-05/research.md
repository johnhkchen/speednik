# T-010-05 Research: Programmed Agents

## Scope

Port the S-008 harness strategies to observation-based agents conforming to the `Agent`
protocol. Each agent reads only the observation vector — no direct `Player` access.

---

## Existing Infrastructure

### Agent Protocol (`speednik/agents/base.py`)

```python
@runtime_checkable
class Agent(Protocol):
    def act(self, obs: np.ndarray) -> int: ...
    def reset(self) -> None: ...
```

Duck-typed via `Protocol` — agents don't inherit, just implement the methods. The
`@runtime_checkable` decorator enables `isinstance(agent, Agent)` checks.

### Action Space (`speednik/agents/actions.py`)

8 discrete actions (0-7): NOOP, LEFT, RIGHT, JUMP, LEFT_JUMP, RIGHT_JUMP, DOWN,
DOWN_JUMP. Each maps to an `InputState` via `ACTION_MAP`.

`action_to_input(action, prev_jump_held) -> (InputState, bool)` handles jump edge
detection — `jump_pressed` is only True on the first frame a jump action appears.
Agents return action ints; the simulation loop handles conversion.

### Observation Vector (`speednik/observation.py`)

12-dim float32 numpy array extracted from SimState:

| Index | Field | Range | Notes |
|-------|-------|-------|-------|
| 0 | x position | 0..1 | normalized by level_width |
| 1 | y position | 0..1 | normalized by level_height |
| 2 | x velocity | -1..1 | normalized by MAX_X_SPEED (16.0) |
| 3 | y velocity | -1..1 | normalized by MAX_X_SPEED |
| 4 | on_ground | 0/1 | boolean flag |
| 5 | ground_speed | -1..1 | normalized by MAX_X_SPEED |
| 6 | is_rolling | 0/1 | boolean flag |
| 7 | facing_right | 0/1 | boolean flag |
| 8 | surface angle | 0..1 | normalized by 255.0 |
| 9 | max progress | 0..1 | max_x_reached / level_width |
| 10 | distance to goal | -1..1 | (goal_x - x) / level_width |
| 11 | time fraction | 0..1 | frame / 3600.0 |

No terrain raycasts yet (obs[18] from spec not available). JumpRunnerAgent must use
alternative heuristics until raycasts arrive in T-010-16/17.

### Package Init (`speednik/agents/__init__.py`)

Currently exports: Agent, all ACTION_* constants, NUM_ACTIONS, ACTION_MAP,
action_to_input. New agents and the registry will be added here.

---

## Harness Strategies to Port (`tests/harness.py`)

### idle()
- Returns `InputState()` every frame
- Direct mapping: always return `ACTION_NOOP`

### hold_right()
- Returns `InputState(right=True)` every frame
- Direct mapping: always return `ACTION_RIGHT`

### hold_right_jump()
- Runs right, holds jump, re-presses jump after landing
- Uses `was_airborne` closure state + `player.physics.on_ground`
- Agent equivalent: track `_was_airborne`, detect landing via obs[4], return
  `ACTION_RIGHT_JUMP` on landing frames, `ACTION_RIGHT` otherwise
- Note: the harness version always holds jump_held=True. The agent version returns
  ACTION_RIGHT_JUMP for jump frames and ACTION_RIGHT for run frames. Edge detection
  in action_to_input handles jump_pressed automatically.

### spindash_right(charge_frames=3, redash_threshold=2.0)
- State machine: CROUCH → CHARGE → RELEASE → RUN
- CROUCH: return down_held (1 frame)
- CHARGE: return down_held + jump_pressed+jump_held for charge_frames
- RELEASE: return right (1 frame, releases spindash)
- RUN: return right; if on_ground and |ground_speed| < threshold → back to CROUCH
- Harness checks `player.state != PlayerState.SPINDASH` — agent cannot check
  PlayerState, must rely on ground_speed and is_rolling. Observation obs[6]
  (is_rolling) is 1.0 during spindash roll — can use this as a proxy.
- redash_threshold (2.0 raw) → normalized: 2.0 / 16.0 = 0.125

### scripted(timeline)
- Harness takes `list[tuple[int, int, InputState]]` — (start_frame, end_frame, inp)
- Agent version: takes timeline as `list[tuple[int, int, int]]` — (start, end, action)
- Must track its own frame counter (incremented each `act()` call)
- `reset()` resets the frame counter to 0

---

## Observation Mapping Concerns

### SpindashAgent — Detecting "should re-dash"

Harness: `player.physics.on_ground and abs(player.physics.ground_speed) < threshold
and player.state != PlayerState.SPINDASH`

Agent equivalent using obs:
- `obs[4] > 0.5` → on_ground
- `abs(obs[5]) < normalized_threshold` → ground_speed below threshold
- `obs[6] < 0.5` → not rolling (proxy for not in SPINDASH state)

The `is_rolling` check is a reasonable proxy: during active spindash the player is
rolling, so we skip re-dash while rolling. This may cause slight behavior differences
(rolling can also occur during downhill sections) but is acceptable.

### JumpRunnerAgent — No raycasts available

Spec §4.2 uses `obs[18]` (forward ray distance) which requires the 26-dim observation
from T-010-16/17. Current obs is 12-dim. Options:

1. Jump periodically on a timer
2. Jump on landing (detected via on_ground transitions)
3. Jump when x velocity drops (obstacle indication)

Option 2 matches the harness `hold_right_jump()` most closely and is deterministic.
It also matches the ticket description: "jump upon landing."

---

## File Layout

Ticket specifies:
- `speednik/agents/hold_right.py`
- `speednik/agents/jump_runner.py`
- `speednik/agents/spindash.py`
- `speednik/agents/scripted.py`
- `speednik/agents/idle.py`
- `speednik/agents/registry.py`

Each module: one class, one file. Registry maps string names to classes.

---

## Testing Strategy

Existing tests in `tests/test_agents.py` (196 lines) cover protocol, actions, and
edge detection. New tests will extend this file.

Acceptance criteria require:
- Protocol conformance (`isinstance` checks)
- Registry resolution with and without params
- Smoke tests: HoldRight moves right over 300 frames
- Smoke tests: Spindash faster than HoldRight over 300 frames
- No Pyxel imports in any agent module

Tests need `create_sim("hillside")`, `extract_observation`, `sim_step`, and
`action_to_input` — all available from existing modules.

---

## Constraints

- No Pyxel imports anywhere in `speednik/agents/`
- No direct `Player` or `PhysicsState` access — agents see only obs vectors
- Agents must be constructable with default args (except ScriptedAgent which needs
  a timeline)
- Registry must support kwargs passthrough for parameterized agents
