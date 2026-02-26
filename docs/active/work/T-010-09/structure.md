# T-010-09 Structure: Scenario YAML Format and Loader

## New Files

### `speednik/scenarios/__init__.py`

Re-exports public API:
- `SuccessCondition`, `FailureCondition`, `StartOverride` from conditions
- `ScenarioDef`, `load_scenario`, `load_scenarios` from loader

### `speednik/scenarios/conditions.py`

Condition dataclasses and validation constants.

```
VALID_SUCCESS_TYPES = {"goal_reached", "position_x_gte", "position_y_lte",
                       "alive_at_end", "rings_gte"}
VALID_FAILURE_TYPES = {"player_dead", "stuck", "any"}

@dataclass SuccessCondition:
    type: str
    value: float | None = None
    min_speed: float | None = None

@dataclass FailureCondition:
    type: str
    tolerance: float | None = None
    window: int | None = None
    conditions: list[FailureCondition] | None = None

@dataclass StartOverride:
    x: float
    y: float
```

No methods, no logic. Pure data + constant sets.

### `speednik/scenarios/loader.py`

ScenarioDef and all loading/parsing functions.

```
@dataclass ScenarioDef:
    name: str
    description: str
    stage: str
    agent: str
    agent_params: dict | None
    max_frames: int
    success: SuccessCondition
    failure: FailureCondition
    metrics: list[str]
    start_override: StartOverride | None = None

def load_scenario(path: Path) -> ScenarioDef
def load_scenarios(paths: list[Path] | None = None,
                   run_all: bool = False,
                   base: Path = Path("scenarios")) -> list[ScenarioDef]
```

Internal helpers (not exported):
```
def _parse_success(data: dict) -> SuccessCondition
def _parse_failure(data: dict) -> FailureCondition
def _parse_start_override(data: dict | None) -> StartOverride | None
def _parse_scenario(data: dict) -> ScenarioDef
```

### `scenarios/hillside_complete.yaml`

```yaml
name: hillside_complete
stage: hillside
agent: spindash
agent_params: {charge_frames: 3, redash_speed: 0.15}
max_frames: 3600
success: {type: goal_reached}
failure: {type: player_dead}
metrics: [completion_time, max_x, rings_collected, death_count, velocity_profile]
```

### `scenarios/hillside_hold_right.yaml`

hold_right agent, goal_reached success, player_dead failure.

### `scenarios/hillside_loop.yaml`

hold_right agent near loop entry, position_x_gte success, compound any failure
(player_dead + stuck).

### `scenarios/pipeworks_jump.yaml`

jump_runner agent, goal_reached success, player_dead failure.

### `scenarios/gap_jump.yaml`

scripted agent with timeline, position_x_gte success, player_dead failure.

### `tests/test_scenarios.py`

Test module for loader functionality.

```
Tests:
- test_load_single_scenario: round-trip hillside_complete.yaml
- test_all_fields_populated: verify every field on ScenarioDef
- test_success_condition_types: each valid type parses
- test_failure_condition_types: each valid type parses
- test_compound_any_condition: nested conditions in any
- test_start_override_optional: present and absent cases
- test_agent_params_optional: present and absent cases
- test_load_scenarios_run_all: globs scenarios/ directory
- test_load_scenarios_explicit_paths: loads specific files
- test_invalid_success_type: ValueError on unknown type
- test_invalid_failure_type: ValueError on unknown type
- test_missing_required_field: KeyError on missing name/stage/etc
- test_no_pyxel_imports: verify scenarios package doesn't import pyxel
```

## Modified Files

### `pyproject.toml`

Add `pyyaml` to dependencies list:
```
dependencies = [
    "pyxel",
    "numpy",
    "gymnasium>=1.2.3",
    "pyyaml",
]
```

## Module Dependency Graph

```
scenarios/conditions.py  (no imports from speednik)
    ↑
scenarios/loader.py      (imports conditions, yaml, pathlib)
    ↑
scenarios/__init__.py    (re-exports)
```

No dependency on simulation, agents, observation, or any Pyxel-related module.
The scenarios package is a pure data layer.

## Interface Contract

The loader produces `ScenarioDef` objects. The runner (future ticket) will consume them:
```python
scenario = load_scenario(Path("scenarios/hillside_complete.yaml"))
agent = resolve_agent(scenario.agent, scenario.agent_params)
sim = create_sim(scenario.stage)
# Runner loops sim_step with agent.act(obs) ...
```

This ticket establishes the data contract. The runner ticket will add the execution loop.

## File Count

- 3 new Python files (scenarios package)
- 5 new YAML files (starter scenarios)
- 1 new test file
- 1 modified file (pyproject.toml)
- Total: 10 files touched
