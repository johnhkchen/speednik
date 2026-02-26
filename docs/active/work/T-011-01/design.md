# T-011-01 Design: Stage Walkthrough Smoke Tests

## Approach Options

### Option A: Raw `sim_step` Loop with Manual Agent Driving

Write a manual loop: `create_sim` → per-frame `extract_observation` → `agent.act(obs)` →
`action_to_input` → `sim_step`. Collect metrics manually (max_x, deaths, rings, stuck
detection) inside the test. Full control, no dependency on scenario runner.

**Pros**: Direct use of `sim_step`/`create_sim` as ticket requests. Full control over
assertions at any point in the loop. No YAML files needed.

**Cons**: Duplicates ~40 lines of loop logic that `run_scenario` already handles. Must
re-implement stuck detection (already exists in scenario runner). Manual metric collection.

### Option B: Use `run_scenario` with Programmatic `ScenarioDef`

Construct `ScenarioDef` objects in-code (no YAML). Call `run_scenario(sd)` and assert on
`ScenarioOutcome` fields. The runner internally uses `create_sim` + `sim_step`, satisfying
the ticket requirement.

**Pros**: Reuses well-tested runner infrastructure. Gets `stuck_at`, `max_x`,
`rings_collected`, `death_count`, `completion_time` metrics for free. Trajectory available
for additional assertions. Deterministic by construction. Much less test code.

**Cons**: Indirect `sim_step` usage (through runner). If runner has a bug, tests might pass
incorrectly. Adds coupling to scenario system.

### Option C: Hybrid — `run_scenario` for Execution, Direct Assertions on SimState

Use `run_scenario` to drive the simulation (it returns `ScenarioOutcome` with metrics and
trajectory), then assert on the outcome's metrics and trajectory data. This uses the scenario
infrastructure for the loop but keeps assertions in test code.

**Pros**: Best of both worlds — reuses loop logic, keeps assertion logic explicit in tests.
Metrics like `stuck_at` come from the runner. Trajectory gives per-frame data for debugging.
Still satisfies "uses sim_step/create_sim" since runner calls them internally.

**Cons**: Same coupling concern as Option B, but mitigated by the scenario module already
having 800+ lines of tests.

## Decision: Option C — Hybrid via `run_scenario`

**Rationale**:
1. The ticket says "use `sim_step` / `create_sim`, not the old harness." The scenario runner
   uses `sim_step`/`create_sim` internally — it IS the new harness. The old harness is
   `tests/harness.py` which uses `player_update` directly.
2. `stuck_at` detection is already implemented in `_metric_stuck_at` (last 120 frames,
   spread < 2.0px). Re-implementing it would be pointless duplication.
3. `run_scenario` returns `ScenarioOutcome` with everything we need: success/reason,
   frames_elapsed, metrics dict, and full trajectory.
4. The scenario system is already thoroughly tested (817 lines in test_scenarios.py).

## Test Structure Design

### Parameterization
Use `pytest.mark.parametrize` with a list of 9 `(stage, agent, agent_params, max_frames)` tuples.

Strategy-to-agent mapping:
- `hold_right` → agent `"hold_right"`, no params
- `hold_right_jump` → agent `"jump_runner"`, no params
- `spindash_right` → agent `"spindash"`, `{charge_frames: 3, redash_speed: 0.15}`

### ScenarioDef Construction
Build `ScenarioDef` in a helper function:
- success: `goal_reached`
- failure: compound `any` with `player_dead` + `stuck` (tolerance=2.0, window=120)
- metrics: `["max_x", "stuck_at", "rings_collected", "death_count", "completion_time"]`
- max_frames: per-stage (hillside: 4000, pipeworks: 5000, skybridge: 6000)

### Assertion Strategy

**Test 1: Forward progress** (all 9 combos)
- `outcome.metrics["max_x"]` exceeds 50% of level width
- `outcome.metrics["stuck_at"]` is None (no soft-lock)

**Test 2: Goal reachability** (selective)
- `spindash_right` on all 3 stages: assert `outcome.success` and `outcome.reason == "goal_reached"`
- Other combos: document behavior. Some may reach goal, some may not — use `pytest.mark.xfail`
  or soft assertions with logging for combos that are known to get stuck.

**Test 3: Deaths within bounds**
- Hillside: all strategies → 0 deaths expected
- Pipeworks/skybridge: deaths < reasonable cap (e.g., 3)

**Test 4: Ring collection**
- `outcome.metrics["rings_collected"] > 0` for all moving strategies

**Test 5: Frame budget**
- If goal reached: `outcome.frames_elapsed <= 6000`

### What Was Rejected

- **Option A** (raw loop): Too much code duplication. The scenario runner exists precisely
  for this use case. Writing a manual loop would reimplement stuck detection, metric
  collection, and event processing — all already tested.

- **Separate YAML scenario files**: The ticket explicitly locates tests in
  `tests/test_walkthrough.py`. YAML files would scatter the test definition across
  `scenarios/` and `tests/`. Programmatic `ScenarioDef` keeps everything in one file.

- **Using `SpeednikEnv`**: The Gymnasium wrapper adds reward computation and observation
  formatting overhead. Walkthrough tests care about game completion, not RL signals.

## Expected Behavior Matrix

| Stage | hold_right | hold_right_jump | spindash_right |
|-------|-----------|-----------------|----------------|
| hillside | likely reaches goal | likely reaches goal | MUST reach goal |
| pipeworks | may get stuck (pipes) | may reach goal | MUST reach goal |
| skybridge | may get stuck (gaps) | may reach goal | MUST reach goal |

This matrix will be refined during implementation when we observe actual behavior.
