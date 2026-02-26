# Plan — T-010-10: scenario-runner-and-conditions

## Step 1: Add check_conditions to conditions.py

Add `check_conditions`, `_check_success`, `_check_failure` to `speednik/scenarios/conditions.py`.

- Import `SimState` from `speednik.simulation`.
- `_check_success` handles: `goal_reached`, `position_x_gte` (with optional min_speed),
  `position_y_lte`, `alive_at_end`, `rings_gte`.
- `_check_failure` handles: `player_dead`, `stuck` (max-min spread over window), `any` (recurse).
- `check_conditions` calls `_check_success` first, then `_check_failure`. First non-None wins.
- Signature: `check_conditions(success, failure, sim, trajectory, frame, max_frames)`.

**Verify:** Write unit tests first (Step 3), then ensure they pass.

## Step 2: Create runner.py with FrameRecord, ScenarioOutcome, run_scenario

Create `speednik/scenarios/runner.py`.

- Define `FrameRecord` and `ScenarioOutcome` dataclasses per spec §6.1.
- Implement `run_scenario(scenario_def)`:
  1. `create_sim(scenario_def.stage)`
  2. Apply `start_override` if present.
  3. `resolve_agent(scenario_def.agent, scenario_def.agent_params)`, `.reset()`.
  4. Frame loop with `prev_jump_held` tracking.
  5. Per frame: `extract_observation` → `agent.act` → `action_to_input` → `sim_step` → reward → `FrameRecord`.
  6. `check_conditions` each frame; break on terminal.
  7. `time.perf_counter` for wall time.
  8. `compute_metrics` for requested metrics.
  9. Return `ScenarioOutcome`.
- Implement `compute_metrics(requested, trajectory, sim, success)`:
  - Dispatch dict mapping metric names to callables.
  - Supported: `completion_time`, `max_x`, `rings_collected`, `death_count`, `total_reward`,
    `average_speed`, `peak_speed`, `time_on_ground`, `stuck_at`.

## Step 3: Update scenarios __init__.py

Add exports: `FrameRecord`, `ScenarioOutcome`, `run_scenario`, `check_conditions`.

## Step 4: Write tests

Extend `tests/test_scenarios.py` with:

**TestCheckConditions** — Unit tests using mock/synthetic SimState objects.
For each condition type, create a minimal SimState (using `create_sim_from_lookup` with
a flat tile grid or by constructing a mock), set the relevant fields, and verify the
condition fires or doesn't fire.

For `stuck`: build a trajectory list of objects with `.x` attribute, verify detection.

**TestFrameRecord / TestScenarioOutcome** — Verify dataclass construction.

**TestComputeMetrics** — Build synthetic trajectories, verify each metric computation.

**TestRunScenario** — Integration tests:
- Load `hillside_hold_right.yaml`, run it, verify outcome fields populated.
- Test start_override moves player.
- Test wall_time_ms > 0.
- Test agent is resolved from YAML.

**TestDeterminism** — Load `hillside_hold_right.yaml`, run twice, assert
`outcome1.trajectory == outcome2.trajectory` field by field.

**TestHillsideComplete** — Load `hillside_complete.yaml`, run, assert no exceptions.

**TestNoPyxelImports** — Add `runner.py` to the no-pyxel check.

## Step 5: Run tests

```
uv run pytest tests/test_scenarios.py -x -v
```

Fix any failures. Also run full suite to ensure no regressions:

```
uv run pytest -x
```

## Step 6: Verify acceptance criteria

Walk through all 15 acceptance criteria in the ticket and verify each is covered by
either implementation or tests.

## Testing strategy

- **Unit tests** for `check_conditions` — one test per condition type, using synthetic
  SimState objects. No real stage loading needed for these.
- **Integration tests** for `run_scenario` — use real stages (hillside). These are slower
  but verify the full pipeline.
- **Determinism test** — run a short scenario (max_frames=300) twice, compare trajectories.
  Use a simple agent (hold_right) to keep it fast.
- **No-Pyxel** — source-level grep for import statements.
- All tests in `tests/test_scenarios.py` as specified by the ticket.
