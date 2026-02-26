# T-010-09 Progress: Scenario YAML Format and Loader

## Completed

### Step 1: Add pyyaml dependency
- Added `"pyyaml"` to `pyproject.toml` dependencies.
- `uv sync` installed pyyaml==6.0.3.

### Step 2: Create conditions module
- Created `speednik/scenarios/conditions.py`.
- Defined `VALID_SUCCESS_TYPES` and `VALID_FAILURE_TYPES` frozen sets.
- Defined `SuccessCondition`, `FailureCondition`, `StartOverride` dataclasses.

### Step 3: Create loader module
- Created `speednik/scenarios/loader.py`.
- Defined `ScenarioDef` dataclass with all fields from ticket.
- Implemented `_parse_success`, `_parse_failure`, `_parse_start_override`, `_parse_scenario`.
- Implemented `load_scenario(path)` and `load_scenarios(paths, run_all, base)`.
- Compound `any` condition with recursive nested parsing works.

### Step 4: Populate __init__.py
- Created `speednik/scenarios/__init__.py` with re-exports and `__all__`.

### Step 5: Write starter scenario YAML files
- Created `scenarios/` directory at project root.
- Wrote 5 scenario files:
  - `hillside_complete.yaml` — spindash, goal_reached/player_dead
  - `hillside_hold_right.yaml` — hold_right, goal_reached/player_dead
  - `hillside_loop.yaml` — hold_right, position_x_gte/compound-any, start_override
  - `pipeworks_jump.yaml` — jump_runner, goal_reached/player_dead
  - `gap_jump.yaml` — scripted with timeline, position_x_gte/player_dead

### Step 6: Write tests
- Created `tests/test_scenarios.py` with 31 tests covering:
  - Real scenario file round-trips (7 tests)
  - Success condition types (6 tests)
  - Failure condition types (3 tests)
  - Optional fields (6 tests)
  - Validation/error cases (6 tests)
  - Constant completeness (2 tests)
  - No-Pyxel-import guard (1 test)

### Step 7: Run full test suite
- `tests/test_scenarios.py`: 31/31 passed.
- Full suite: 966 passed, 5 xfailed, 0 failures.

## Deviations from Plan

None. All steps executed as planned.
