# T-010-12 Review: Trajectory Serialization & Metrics

## Changes Summary

### Files Modified

| File | Lines Changed | Description |
|------|--------------|-------------|
| `speednik/scenarios/runner.py` | +10, ~4 modified | Added velocity_profile metric + dispatch entry; changed compute_metrics to raise ValueError on unknown metric names |
| `tests/test_scenarios.py` | +120, ~8 modified | Added 10 new tests, replaced 1 test; new TestRoundTrip class |

### No Files Created or Deleted

All changes are modifications to existing files.

---

## Acceptance Criteria Evaluation

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All 9 metrics computed correctly | PASS | Unit tests for all 9 metrics pass (completion_time, max_x, rings_collected, death_count, total_reward, average_speed, peak_speed, time_on_ground, stuck_at) |
| compute_metrics only computes requested | PASS | `test_only_requested_metrics_computed` verifies only requested keys appear |
| Unknown metric raises ValueError | PASS | `test_unknown_metric_raises_valueerror` asserts ValueError with clear message |
| velocity_profile returns full x_vel list | PASS | `test_velocity_profile` verifies list contents |
| JSON output format correct | PASS | `test_round_trip_basic` verifies name, success, reason, frames_elapsed, wall_time_ms, metrics |
| Trajectory omitted by default | PASS | `test_save_without_trajectory` (pre-existing) |
| Trajectory included with --trajectory | PASS | `test_cli_trajectory_flag` (pre-existing) + `test_round_trip_with_trajectory` |
| JSON valid and parseable | PASS | All round-trip tests use json.loads successfully |
| Round-trip save/load/compare | PASS | 3 round-trip tests: basic, with trajectory, null metrics |
| stuck_at uses sliding window | PASS | 3 stuck_at tests cover stuck/not-stuck/short-trajectory cases |
| No Pyxel imports | PASS | `test_scenarios_package_no_pyxel` + `test_cli_modules_no_pyxel` (pre-existing) |
| `uv run pytest tests/ -x` passes | PASS | 1079 passed, 16 skipped, 5 xfailed |

---

## Test Coverage

### New Tests (10)
- `test_death_count`
- `test_stuck_at_stuck`
- `test_stuck_at_not_stuck`
- `test_stuck_at_short_trajectory`
- `test_velocity_profile`
- `test_unknown_metric_raises_valueerror`
- `test_empty_trajectory_metrics`
- `test_only_requested_metrics_computed`
- `test_round_trip_basic`
- `test_round_trip_with_trajectory`
- `test_round_trip_null_metrics`

### Modified Tests (1)
- `test_unknown_metric_ignored` → `test_unknown_metric_raises_valueerror`

### Total test_scenarios.py count: 101 (was 91)

### Coverage Gaps
- No test for velocity_profile with negative x_vel values (minor — the metric is
  a trivial list comprehension)
- No test for very large trajectories (3600 frames) — covered implicitly by
  integration tests (TestHillsideComplete, TestRunScenario)

---

## Behavioral Change

`compute_metrics` now raises `ValueError` for unknown metric names instead of
silently skipping them. This is intentional per acceptance criteria. All scenario
YAML files in the repo only request known metrics (hillside_complete.yaml requests
velocity_profile, which is now registered). Any external YAML files referencing
made-up metric names will now fail with a clear error.

---

## Open Concerns

None. The implementation is minimal and all acceptance criteria are met. The
ticket mentioned creating `speednik/scenarios/metrics.py` and extending
`speednik/scenarios/output.py`, but both were unnecessary — the metric functions
were already in runner.py and the serialization was already complete in output.py.
The design rationale for keeping code in its existing location is documented in
design.md.
