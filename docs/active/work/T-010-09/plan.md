# T-010-09 Plan: Scenario YAML Format and Loader

## Step 1: Add pyyaml dependency

- Add `"pyyaml"` to `dependencies` in `pyproject.toml`.
- Run `uv sync` to install.
- Verify: `uv run python -c "import yaml; print(yaml.__version__)"`.

## Step 2: Create conditions module

Create `speednik/scenarios/__init__.py` (empty initially) and
`speednik/scenarios/conditions.py` with:

- `VALID_SUCCESS_TYPES` and `VALID_FAILURE_TYPES` frozen sets.
- `SuccessCondition` dataclass: type, value, min_speed.
- `FailureCondition` dataclass: type, tolerance, window, conditions.
- `StartOverride` dataclass: x, y.

Verify: import from Python REPL, instantiate each dataclass.

## Step 3: Create loader module

Create `speednik/scenarios/loader.py` with:

- `ScenarioDef` dataclass with all fields from ticket spec.
- `_parse_success(data)` — validates type against VALID_SUCCESS_TYPES, returns dataclass.
- `_parse_failure(data)` — validates type, handles compound `any` recursively.
- `_parse_start_override(data)` — returns None or StartOverride.
- `_parse_scenario(data)` — orchestrates field extraction and sub-parsers.
- `load_scenario(path: Path) -> ScenarioDef` — reads YAML file, calls _parse_scenario.
- `load_scenarios(paths, run_all, base)` — multi-file loader with glob support.

Verify: unit test imports work.

## Step 4: Populate `__init__.py` with re-exports

Update `speednik/scenarios/__init__.py` to re-export:
- From conditions: SuccessCondition, FailureCondition, StartOverride,
  VALID_SUCCESS_TYPES, VALID_FAILURE_TYPES.
- From loader: ScenarioDef, load_scenario, load_scenarios.
- Define `__all__`.

## Step 5: Write starter scenario YAML files

Create `scenarios/` directory at project root. Write 5 files:

1. `hillside_complete.yaml` — spindash agent, goal_reached, standard metrics.
2. `hillside_hold_right.yaml` — hold_right agent, goal_reached.
3. `hillside_loop.yaml` — hold_right, position_x_gte past loop, compound any failure.
4. `pipeworks_jump.yaml` — jump_runner agent on pipeworks.
5. `gap_jump.yaml` — scripted agent with timeline, position_x_gte.

Verify: each file is valid YAML (`yaml.safe_load` doesn't error).

## Step 6: Write tests

Create `tests/test_scenarios.py` with:

- Round-trip test: load hillside_complete.yaml, verify all fields.
- Condition type coverage: each of 5 success types, each of 3 failure types.
- Compound `any` condition with nested sub-conditions.
- Optional fields: start_override present/absent, agent_params present/absent.
- `load_scenarios(run_all=True)` finds all 5 YAML files.
- `load_scenarios(paths=[...])` loads specific files.
- Error cases: invalid success type, invalid failure type, missing required field.
- No-Pyxel-import check on scenarios package.

## Step 7: Run full test suite

- `uv run pytest tests/test_scenarios.py -v` — new tests pass.
- `uv run pytest tests/ -x` — full suite passes (no regressions).

## Testing Strategy

- **Unit tests** for each parser function via round-trip loading.
- **Validation tests** for error paths (bad types, missing fields).
- **Integration test** via `load_scenarios(run_all=True)` loading real YAML files.
- **Guard test** for no Pyxel imports in scenarios package.
- No simulation or agent execution needed — this is a pure data layer.

## Commit Strategy

- Single commit after all files are written and tests pass.
- Message: `feat: add scenario YAML format and loader (T-010-09)`.
