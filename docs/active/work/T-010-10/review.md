# Review — T-010-10: scenario-runner-and-conditions

## Summary of changes

### Files created
- `speednik/scenarios/runner.py` — 230 lines. Contains `FrameRecord`, `ScenarioOutcome`
  dataclasses, `_compute_reward` (mirrors env.py formula), `compute_metrics` with 9-metric
  dispatch table, and `run_scenario` orchestrating the full frame loop.

### Files modified
- `speednik/scenarios/conditions.py` — Added ~80 lines: `check_conditions`,
  `_check_success`, `_check_failure`. Implements all 8 condition types from spec §5.2.
  Added `TYPE_CHECKING` guard for `SimState` import.
- `speednik/scenarios/__init__.py` — Added exports for `check_conditions`, `FrameRecord`,
  `ScenarioOutcome`, `run_scenario`. Updated module docstring.
- `tests/test_scenarios.py` — Added 37 new tests across 7 test classes. Total: 68 tests.

### Files not modified
- `speednik/simulation.py`, `speednik/observation.py`, `speednik/env.py`,
  `speednik/agents/*`, `speednik/scenarios/loader.py` — no changes needed.

## Acceptance criteria verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `run_scenario` executes ScenarioDef, returns ScenarioOutcome | Pass | `TestRunScenario::test_run_scenario_hold_right_hillside` |
| 2 | Start override repositions player | Pass | `TestRunScenario::test_run_scenario_start_override` |
| 3 | Agent resolved from registry and reset | Pass | `TestRunScenario::test_run_scenario_agent_resolved` |
| 4 | Per-frame FrameRecord collected | Pass | `TestRunScenario::test_run_scenario_trajectory_has_frame_records` |
| 5 | `goal_reached` success condition | Pass | `TestCheckConditions::test_success_goal_reached_fires` |
| 6 | `position_x_gte` success condition | Pass | `test_success_position_x_gte`, `_with_min_speed_pass`, `_fail` |
| 7 | `alive_at_end` success condition | Pass | `test_success_alive_at_end_fires`, `_not_yet` |
| 8 | `player_dead` failure condition | Pass | `test_failure_player_dead`, `_not_yet` |
| 9 | `stuck` failure condition | Pass | `test_failure_stuck`, `_not_enough_frames`, `_moving` |
| 10 | Compound `any` failure | Pass | `test_failure_any_first_triggers`, `_none_triggers` |
| 11 | `wall_time_ms` measured via perf_counter | Pass | `test_run_scenario_wall_time_measured` |
| 12 | Determinism: identical trajectories | Pass | `TestDeterminism::test_two_runs_identical_trajectory` |
| 13 | `hillside_complete.yaml` runs | Pass | `TestHillsideComplete::test_hillside_complete_runs_without_errors` |
| 14 | No Pyxel imports | Pass | `TestNoPyxelImports::test_scenarios_package_no_pyxel` (includes runner.py) |
| 15 | `uv run pytest tests/test_scenarios.py -x` passes | Pass | 68 passed in 0.33s |

## Test coverage

**New tests added: 37** (31 existed from T-010-07)

| Test class | Count | Coverage |
|------------|-------|----------|
| `TestCheckConditions` | 18 | All 8 condition types, edge cases, priority |
| `TestFrameRecord` | 1 | Dataclass construction |
| `TestScenarioOutcome` | 1 | Dataclass construction |
| `TestComputeMetrics` | 9 | All 8 computed metrics + unknown metric handling |
| `TestRunScenario` | 6 | Integration: hold_right, start override, wall time, agent, trajectory, metrics |
| `TestDeterminism` | 1 | Two identical runs compared field-by-field |
| `TestHillsideComplete` | 1 | Full 3600-frame scenario completion |

**Full suite:** 1011 passed, 5 xfailed, 0 regressions.

## Design decisions made

1. **Reward not extracted to shared function** — Runner duplicates env.py's reward formula
   (~15 lines) to avoid refactoring env.py. Low drift risk; can unify later.
2. **check_conditions takes condition objects, not ScenarioDef** — Avoids circular import
   between conditions.py and loader.py.
3. **stuck uses max-min spread, not variance** — Simpler, maps directly to "moved less
   than N pixels in M frames."
4. **Metrics dispatch dict** — Cleaner than if-chain for 9 metrics.

## Open concerns

1. **Reward drift** — `_compute_reward` in runner.py mirrors env.py's `_compute_reward`.
   If env.py's reward changes, runner.py must be updated manually. Consider extracting a
   shared function in a future ticket.
2. **velocity_profile metric** — Listed in `hillside_complete.yaml` but not implemented
   (it's an array, not a scalar). `compute_metrics` silently skips unknown metric names.
   Should be addressed when trajectory serialization is implemented.
3. **stuck_at metric** — Uses hardcoded window=120, tolerance=2.0. These could be made
   configurable or derived from the scenario's failure condition parameters.
4. **Large trajectory memory** — `hillside_complete.yaml` with 3600 frames produces 3600
   FrameRecord objects. Not a problem at current scale but worth noting for batch runs.
