# T-010-09 Research: Scenario YAML Format and Loader

## Scope

Define a YAML scenario format and build a loader that parses scenario files into typed
Python dataclasses. No runner logic — just the data layer.

## Existing Codebase Inventory

### Simulation Layer (Layer 2) — `speednik/simulation.py`

- `SimState` dataclass holds all game state: player, entities, metrics, terminal flags.
- `create_sim(stage_name: str) -> SimState` — factory from stage name string.
- `sim_step(sim, inp) -> list[Event]` — pure headless step, no Pyxel.
- Terminal state fields: `goal_reached: bool`, `player_dead: bool`.
- Metric fields: `frame`, `max_x_reached`, `rings_collected`, `deaths`.
- Event types: `RingCollectedEvent`, `DamageEvent`, `DeathEvent`, `SpringEvent`,
  `GoalReachedEvent`, `CheckpointEvent`.

### Agent System (Layer 3) — `speednik/agents/`

- `Agent` Protocol: `act(obs: ndarray) -> int`, `reset() -> None`.
- 5 agents registered in `AGENT_REGISTRY`: idle, hold_right, jump_runner, spindash, scripted.
- `resolve_agent(name: str, params: dict | None)` — instantiates from registry with kwargs.
- SpindashAgent params: `charge_frames`, `redash_speed`.
- ScriptedAgent params: `timeline: list[tuple[int, int, int]]`.

### Observation (Layer 2.5) — `speednik/observation.py`

- `OBS_DIM = 12`, `extract_observation(sim) -> ndarray` (float32).
- Positions normalized by level dimensions; velocities by MAX_X_SPEED.

### Action Space — `speednik/agents/actions.py`

- 8 discrete actions (0-7) mapped via `action_to_input(action, prev_jump_held)`.
- `ACTION_NOOP`, `ACTION_LEFT`, `ACTION_RIGHT`, `ACTION_JUMP`, etc.

### Gymnasium Environment (Layer 5) — `speednik/env.py`

- `SpeednikEnv(stage, render_mode, max_steps)` — wraps simulation.
- Termination: goal_reached OR player_dead. Truncation: step_count >= max_steps.

### Stage System — `speednik/level.py`, `speednik/stages/`

- `load_stage(name)` — supports "hillside", "pipeworks", "skybridge".
- Stage dataclass: name, player_start, tile_lookup, entities, level_width, level_height.

### Test Infrastructure — `tests/harness.py`

- `ScenarioResult` with `max_x`, `quadrants_visited`, `stuck_at(tolerance, window)`.
- `run_on_stage(stage_name, strategy, max_frames)` — runs a strategy on a real stage.
- Strategies are `Callable[[int, Player], InputState]` — different from Agent protocol.
- The harness predates the Agent system; scenarios will supersede it.

### Project Config — `pyproject.toml`

- Dependencies: pyxel, numpy, gymnasium>=1.2.3.
- Dev dependencies: pytest>=9.0.2, librosa.
- pyyaml is NOT yet a dependency — needs to be added.

## Spec Requirements (§5.1–5.2)

### YAML Fields

Required: name, description, stage, agent, max_frames, success, failure, metrics.
Optional: agent_params (dict), start_override (x, y).

### Condition Types (8 total)

Success conditions: goal_reached, position_x_gte, position_y_lte, alive_at_end, rings_gte.
Failure conditions: player_dead, stuck, any (compound).
Some types appear on both sides (goal_reached as success, player_dead as failure).

### Compound Conditions

The `any` type has a `conditions` list of sub-conditions (recursive nesting).

### Metric Names

Enumerated: completion_time, max_x, rings_collected, death_count, velocity_profile.
These are just strings in the scenario def — the runner (T-010-10+) will compute them.

## Dependencies and Boundaries

### Upstream Dependencies (satisfied)

- T-010-06 (SpeednikEnv) — complete. Agents, simulation, observation all working.

### What This Ticket Produces

- `speednik/scenarios/` package: `__init__.py`, `loader.py`, `conditions.py`.
- `scenarios/` directory at project root with 3-5 YAML files.
- pyyaml dependency added to pyproject.toml.

### What This Ticket Does NOT Produce

- No runner logic (that's T-010-10 or later).
- No metric computation.
- No CLI entry point.
- No condition evaluation at runtime — just data definitions.

## Constraints

- No Pyxel imports anywhere in `speednik/scenarios/`.
- Must use PyYAML for parsing (standard for YAML in Python ecosystem).
- Dataclasses should be plain Python — no pydantic or attrs.
- `load_scenarios(run_all=True)` must glob `scenarios/*.yaml` from the project root.
- Condition types should be validated at load time (fail fast on unknown types).

## Key Patterns Observed

- The codebase uses `from __future__ import annotations` consistently.
- Dataclasses use `@dataclass` with default values for optional fields.
- Type unions use `X | None` syntax (Python 3.10+).
- Factory functions follow `create_*` or `load_*` naming.
- Each module has a docstring in the format `"""speednik/module — description."""`.
- Tests are in `tests/test_*.py`, use pytest, and import directly from speednik.
