# T-010-12 Research: Trajectory Serialization & Metrics

## Summary

This ticket adds the `velocity_profile` metric, enforces unknown-metric errors in
`compute_metrics`, and writes comprehensive tests covering all 9+1 metrics, JSON
serialization round-trips, and trajectory inclusion/exclusion. The infrastructure
from T-010-11 already provides ~95% of the code; the remaining work is small but
test-heavy.

---

## Existing Metric Implementation (runner.py:106-202)

All 9 per-scenario metrics from the spec are already implemented as individual
functions in `speednik/scenarios/runner.py`:

| Function                   | Lines   | Returns              |
|---------------------------|---------|----------------------|
| `_metric_completion_time` | 106-109 | `int\|None`          |
| `_metric_max_x`           | 112-117 | `float`              |
| `_metric_rings_collected` | 120-123 | `int`                |
| `_metric_death_count`     | 126-129 | `int`                |
| `_metric_total_reward`    | 132-135 | `float`              |
| `_metric_average_speed`   | 138-143 | `float`              |
| `_metric_peak_speed`      | 146-151 | `float`              |
| `_metric_time_on_ground`  | 154-159 | `float`              |
| `_metric_stuck_at`        | 162-174 | `float\|None`        |

Each takes `(trajectory, sim, success)` and is registered in `_METRIC_DISPATCH`
(lines 177-187).

### Missing: velocity_profile

The ticket and spec mention `velocity_profile` as a special metric that returns the
full list of `x_vel` values. It is referenced in `hillside_complete.yaml`'s metrics
list but has **no implementation** — no function, no dispatch entry. Currently
`compute_metrics` silently ignores unknown names (lines 198-201).

### Missing: ValueError on unknown metric

The ticket's acceptance criteria require: "Unknown metric name raises ValueError
with clear message." Current behavior: unknown names are silently skipped (line 200:
`if func is not None`). The existing test `test_unknown_metric_ignored` on line 651
asserts this silent-skip behavior. This test **must change** to expect a ValueError.

---

## Existing Serialization (output.py)

`save_results()` (lines 93-102) already:
- Converts `ScenarioOutcome` to dict via `dataclasses.asdict()`
- Strips `trajectory` when `include_trajectory=False`
- Writes pretty-printed JSON with indent=2
- Creates parent directories

`_outcome_to_dict()` (lines 83-90) handles the trajectory toggle.

The JSON structure already matches the spec format (name, success, reason,
frames_elapsed, wall_time_ms, metrics, trajectory).

---

## Existing Test Coverage (test_scenarios.py)

### Metric tests (TestComputeMetrics, lines 563-658)
- Tests for: completion_time (success/failure), max_x, rings_collected,
  total_reward, average_speed, peak_speed, time_on_ground
- Missing tests: death_count, stuck_at, velocity_profile
- `test_unknown_metric_ignored` — asserts wrong behavior (silent skip vs ValueError)

### Output tests (TestSaveResults, lines 918-981)
- test_save_basic, test_save_without_trajectory, test_save_with_trajectory
- test_save_creates_parent_dirs, test_save_metrics_serialized
- Missing: round-trip test (save → load → compare all fields)

### Integration tests (TestRunScenario, lines 666-757)
- Already test metrics_computed, trajectory has frame records
- Determinism tests verify full trajectory equality across runs

---

## FrameRecord Structure (runner.py:27-42)

13 fields: frame, x, y, x_vel, y_vel, ground_speed, angle, on_ground, state,
action, reward, rings, events. All are JSON-serializable natively (`dataclasses.asdict`
handles the list[str] events field correctly).

## SimState Fields Used by Metrics (simulation.py)

- `sim.rings_collected` — used by `_metric_rings_collected`
- `sim.deaths` — used by `_metric_death_count`
- `sim.max_x_reached` — tracked by sim_step but metric uses trajectory max

## Scenario YAML metrics Field

Five scenario files define metrics lists:
- `hillside_complete.yaml`: completion_time, max_x, rings_collected, death_count, velocity_profile
- `hillside_loop.yaml`: max_x, completion_time
- `gap_jump.yaml`: max_x, completion_time
- `pipeworks_jump.yaml`: completion_time, max_x, rings_collected, death_count
- `hillside_hold_right.yaml`: completion_time, max_x, death_count

Only `hillside_complete.yaml` requests `velocity_profile`. None request total_reward,
average_speed, peak_speed, or time_on_ground (though those may be added by future
scenarios).

---

## stuck_at Implementation Detail

`_metric_stuck_at` (lines 162-174) uses a sliding window of the last 120 frames.
If `max(xs) - min(xs) < 2.0`, the player is stuck. This reuses the same concept
as the failure condition `stuck` check in conditions.py. The window size (120) and
tolerance (2.0) are hardcoded in the metric function rather than configurable.

---

## Key Constraints

1. **No Pyxel imports** — all scenarios code must remain Pyxel-free
2. **Deterministic** — metrics derived from trajectory are deterministic
3. **Row-oriented JSON** — spec says "for now, row-oriented JSON is fine"
4. **Trajectory is large** — 3600 frames x 13 fields, but gated by --trajectory flag

---

## Files to Touch

| File | Change |
|------|--------|
| `speednik/scenarios/runner.py` | Add velocity_profile, fix compute_metrics ValueError |
| `tests/test_scenarios.py` | Add metric/serialization tests, fix existing test |
