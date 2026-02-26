# Research — T-010-11: scenario-cli-entry-point

## Objective

Build the CLI entry point for running scenarios from the command line. The CLI is the developer's primary interface for executing test scenarios, comparing results, and validating changes.

## Existing Infrastructure

### Scenario System (Layer 4)

The scenario subsystem is fully implemented across three modules:

- **`speednik/scenarios/loader.py`** — `ScenarioDef` dataclass, `load_scenario(Path)`, `load_scenarios(paths, run_all, base)`. YAML parsing with validation for success/failure condition types, start overrides, agent params.
- **`speednik/scenarios/conditions.py`** — `SuccessCondition`, `FailureCondition`, `StartOverride`, `check_conditions()`. Supports: goal_reached, position_x_gte, position_y_lte, alive_at_end, rings_gte (success); player_dead, stuck, any (failure).
- **`speednik/scenarios/runner.py`** — `FrameRecord`, `ScenarioOutcome`, `run_scenario(ScenarioDef)`, `compute_metrics()`. Full frame loop with trajectory collection, reward computation, wall-clock timing. Nine metric types dispatched via `_METRIC_DISPATCH`.
- **`speednik/scenarios/__init__.py`** — Re-exports all public symbols from the three submodules.

### Agent System (Layer 3)

- **`speednik/agents/registry.py`** — `AGENT_REGISTRY` maps name strings to agent classes. `resolve_agent(name, params)` instantiates with optional kwargs. Five agents registered: idle, hold_right, jump_runner, spindash, scripted.
- **`speednik/agents/actions.py`** — 8 discrete actions. `action_to_input(action, prev_jump_held)` maps action int to `InputState`.

### Simulation (Layer 2)

- **`speednik/simulation.py`** — `SimState`, `create_sim(stage_name)`, `sim_step(sim, inp)`. Deterministic. No Pyxel imports.

### Scenario YAML Files

Five YAML files exist in `scenarios/`:
- `hillside_complete.yaml` — spindash agent, goal_reached, 3600 frames
- `hillside_hold_right.yaml` — hold_right agent, goal_reached, 3600 frames
- `hillside_loop.yaml` — hold_right with start_override, compound failure (any: player_dead, stuck)
- `pipeworks_jump.yaml` — jump_runner agent, goal_reached, 3600 frames
- `gap_jump.yaml` — scripted agent with timeline, position_x_gte success

### Entry Points

- **No `__main__.py`** exists anywhere in the source package. The game runs via `uv run python -m speednik.main`.
- **No `[project.scripts]`** in pyproject.toml.
- The justfile has `up` and `debug` recipes but no test or scenario recipes.

### Test Infrastructure

- `tests/test_scenarios.py` — 52+ tests covering loader, conditions, runner, metrics, determinism. Uses `SCENARIOS_DIR = Path("scenarios")` relative to project root.
- Tests run via `uv run pytest tests/ -x`.

### Dependencies

- `pyyaml` — already a dependency (used by loader.py)
- `argparse` — stdlib, no additional deps needed
- No Pyxel imports in any scenario/agent/simulation module

## Key Constraints

1. **No Pyxel imports** — hard requirement for headless CLI. All scenario infrastructure already satisfies this.
2. **Exit codes** — exit 0 on all-pass, exit 1 on any failure, for CI pipeline compatibility.
3. **TTY detection** — color output (green/red) when stdout is a TTY, plain text otherwise.
4. **Trajectory omission** — trajectories can be 3600 frames x 12 fields = ~43K entries. Omit from JSON by default; include with `--trajectory`.
5. **Comparison placeholder** — `--compare` is a placeholder per ticket; full implementation in T-010-13.
6. **`python -m speednik.scenarios`** must work as an alias for `python -m speednik.scenarios.cli`.

## Interfaces to Consume

The CLI needs to call:
- `load_scenarios(paths, run_all, base)` — already accepts list of Paths and run_all flag
- `run_scenario(scenario_def)` — returns `ScenarioOutcome` with all needed data
- `ScenarioDef.agent` — mutable string field, can be overridden before `run_scenario`

## Output Format (from ticket)

```
PASS  hillside_complete     1847 frames  42.3ms  max_x=3200.5
FAIL  hillside_hold_right   3600 frames  98.1ms  max_x=1456.2  stuck_at=1456.2
```

Key metrics to display inline: `max_x` always, plus `stuck_at` if present.

## JSON Output Format (from spec)

```json
{
  "name": "hillside_complete",
  "success": true,
  "reason": "goal_reached",
  "frames_elapsed": 1847,
  "wall_time_ms": 42.3,
  "metrics": { ... },
  "trajectory": [ ... ]  // only with --trajectory
}
```

## Files to Create

Per ticket:
- `speednik/scenarios/cli.py` — main CLI logic
- `speednik/scenarios/__main__.py` — entry point (`python -m speednik.scenarios`)
- `speednik/scenarios/output.py` — print_outcome, save_results (JSON serialization)

## Observations

1. `load_scenarios` already handles both explicit paths and `--all` glob. The CLI just needs to bridge argparse args to this function.
2. `ScenarioOutcome` is a plain dataclass — serialization to JSON requires `dataclasses.asdict()` or manual dict construction.
3. The `velocity_profile` metric in `hillside_complete.yaml` is silently ignored (not in `_METRIC_DISPATCH`). Not a CLI concern.
4. `run_scenario` already measures wall_time_ms. No additional timing needed in the CLI.
5. The loader uses `Path("scenarios")` as default base — CLI should respect this.
