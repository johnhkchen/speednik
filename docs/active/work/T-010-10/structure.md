# Structure — T-010-10: scenario-runner-and-conditions

## Files modified

### speednik/scenarios/conditions.py

**Add:** `check_conditions(scenario, sim, trajectory, frame)` function.

- Import `SimState` from simulation.py (already no-Pyxel).
- Import `FrameRecord` from runner.py (new, circular-safe since conditions has no runner imports).

Wait — circular import risk: conditions.py would import FrameRecord from runner.py, and
runner.py imports check_conditions from conditions.py. Solution: `check_conditions` takes
`trajectory: list[FrameRecord]` but only accesses `.x` attribute. Use `from __future__
import annotations` to make the type hint lazy, and import FrameRecord inside the function
body OR accept `list[Any]` and document.

Better solution: `check_conditions` only needs trajectory for `stuck` detection. It can
accept `trajectory` typed as `list` (no FrameRecord dependency) and access `.x` by duck
typing. The function signature:

```python
def check_conditions(
    scenario: ScenarioDef,
    sim: SimState,
    trajectory: list,
    frame: int,
    max_frames: int,
) -> tuple[bool | None, str | None]:
```

This avoids any circular imports. The `trajectory` list contains objects with `.x` attribute.

**Imports added:** `SimState` from `speednik.simulation`, `ScenarioDef` from
`speednik.scenarios.loader`.

Wait — `ScenarioDef` is in loader.py, and loader.py imports from conditions.py. Circular!
Solution: pass the condition objects directly instead of ScenarioDef:

```python
def check_conditions(
    success: SuccessCondition,
    failure: FailureCondition,
    sim: SimState,
    trajectory: list,
    frame: int,
    max_frames: int,
) -> tuple[bool | None, str | None]:
```

Now conditions.py only needs: `SuccessCondition`, `FailureCondition` (already defined here),
and `SimState` (from simulation.py). No circular imports.

Internal helpers:
- `_check_success(cond: SuccessCondition, sim, trajectory, frame, max_frames) -> tuple[bool|None, str|None]`
- `_check_failure(cond: FailureCondition, sim, trajectory, frame) -> tuple[bool|None, str|None]`

### speednik/scenarios/runner.py (NEW)

**Exports:** `run_scenario`, `ScenarioOutcome`, `FrameRecord`, `compute_metrics`.

```python
@dataclass
class FrameRecord:
    frame: int
    x: float
    y: float
    x_vel: float
    y_vel: float
    ground_speed: float
    angle: int
    on_ground: bool
    state: str          # PlayerState.value
    action: int
    reward: float
    rings: int
    events: list[str]

@dataclass
class ScenarioOutcome:
    name: str
    success: bool
    reason: str
    frames_elapsed: int
    metrics: dict[str, Any]
    trajectory: list[FrameRecord]
    wall_time_ms: float

def run_scenario(scenario_def: ScenarioDef) -> ScenarioOutcome: ...
def compute_metrics(requested: list[str], trajectory: list[FrameRecord],
                    sim: SimState, success: bool) -> dict[str, Any]: ...
```

Imports:
- `time` (stdlib)
- `SimState`, `create_sim`, `sim_step`, `RingCollectedEvent` from simulation
- `extract_observation` from observation
- `action_to_input` from agents.actions
- `resolve_agent` from agents.registry
- `ScenarioDef` from scenarios.loader
- `check_conditions` from scenarios.conditions
- `MAX_X_SPEED` from constants

### speednik/scenarios/__init__.py

**Add exports:** `FrameRecord`, `ScenarioOutcome`, `run_scenario`, `check_conditions`.

### tests/test_scenarios.py

**Add test classes:**

```
TestCheckConditions
    test_success_goal_reached_fires()
    test_success_goal_reached_not_yet()
    test_success_position_x_gte()
    test_success_position_x_gte_with_min_speed_pass()
    test_success_position_x_gte_with_min_speed_fail()
    test_success_position_y_lte()
    test_success_alive_at_end_fires_at_max()
    test_success_alive_at_end_not_yet()
    test_success_rings_gte()
    test_failure_player_dead()
    test_failure_player_dead_not_yet()
    test_failure_stuck()
    test_failure_stuck_not_enough_frames()
    test_failure_any_first_triggers()
    test_failure_any_none_triggers()

TestFrameRecord
    test_frame_record_fields()

TestScenarioOutcome
    test_scenario_outcome_fields()

TestComputeMetrics
    test_completion_time_success()
    test_completion_time_failure()
    test_max_x()
    test_rings_collected()
    test_total_reward()
    test_average_speed()
    test_peak_speed()
    test_time_on_ground()

TestRunScenario
    test_run_scenario_hold_right_hillside()
    test_run_scenario_start_override()
    test_run_scenario_wall_time_measured()
    test_run_scenario_agent_resolved()

TestDeterminism
    test_two_runs_identical_trajectory()

TestHillsideComplete
    test_hillside_complete_runs_without_errors()

TestNoPyxelImports (extend existing)
    test_runner_no_pyxel()
```

## Files NOT modified

- `speednik/simulation.py` — No changes.
- `speednik/observation.py` — No changes.
- `speednik/env.py` — No changes (reward not extracted to shared function).
- `speednik/agents/*` — No changes.
- `speednik/scenarios/loader.py` — No changes.

## Dependency graph

```
conditions.py  ←──  runner.py  ←──  tests/test_scenarios.py
     │                  │
     ▼                  ▼
 SimState          create_sim, sim_step,
 (simulation.py)   extract_observation,
                   action_to_input,
                   resolve_agent
```

No circular dependencies. conditions.py gains a SimState import but no runner imports.
