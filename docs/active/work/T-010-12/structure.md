# T-010-12 Structure: Trajectory Serialization & Metrics

## Files Modified

### 1. speednik/scenarios/runner.py

**Add velocity_profile metric function** (after `_metric_stuck_at`, before dispatch dict):
```
def _metric_velocity_profile(
    trajectory: list[FrameRecord], sim: SimState, success: bool,
) -> list[float]:
    return [r.x_vel for r in trajectory]
```

**Add dispatch entry** in `_METRIC_DISPATCH`:
```
"velocity_profile": _metric_velocity_profile,
```

**Change compute_metrics** to raise ValueError for unknown names:
```python
def compute_metrics(...) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in requested:
        func = _METRIC_DISPATCH.get(name)
        if func is None:
            raise ValueError(
                f"Unknown metric: {name!r}. "
                f"Valid metrics: {sorted(_METRIC_DISPATCH)}"
            )
        result[name] = func(trajectory, sim, success)
    return result
```

### 2. tests/test_scenarios.py

**Modify TestComputeMetrics class** — add/change these test methods:

- `test_death_count` — Set `sim.deaths = 3`, verify result is 3
- `test_stuck_at_stuck` — Build 120-frame trajectory at constant x, verify returns float
- `test_stuck_at_not_stuck` — Build trajectory with moving x, verify returns None
- `test_stuck_at_short_trajectory` — Build 10-frame trajectory at constant x, verify
  handles window clamping correctly
- `test_velocity_profile` — Build trajectory with known x_vel values, verify list
- `test_unknown_metric_raises_valueerror` — Replace existing `test_unknown_metric_ignored`
- `test_empty_trajectory_metrics` — Verify all metrics handle [] gracefully
- `test_only_requested_metrics_computed` — Request subset, verify only those keys

**Add TestRoundTrip class** after TestSaveResults:

- `test_round_trip_basic` — Save outcomes → load → verify name, success, reason,
  frames_elapsed, wall_time_ms, metrics match
- `test_round_trip_with_trajectory` — Save with trajectory → load → verify
  trajectory[0] fields match
- `test_round_trip_metrics_types` — Verify int stays int, float stays float,
  None stays null/None after round-trip

---

## Files NOT Modified

- `speednik/scenarios/output.py` — Already complete
- `speednik/scenarios/cli.py` — Already complete
- `speednik/scenarios/__init__.py` — No new exports needed (compute_metrics is
  internal; tests import directly from runner)
- `speednik/scenarios/loader.py` — No changes
- `speednik/scenarios/conditions.py` — No changes
- `speednik/observation.py` — No changes
- `speednik/simulation.py` — No changes
- `speednik/env.py` — No changes
- Scenario YAML files — No changes (hillside_complete.yaml already lists
  velocity_profile)

## Module Boundaries

No new modules created. All changes stay within existing file boundaries:
- runner.py: metric computation (internal to scenarios package)
- test_scenarios.py: test coverage (test suite)

## Interface Changes

- `compute_metrics()` now raises `ValueError` for unknown metric names instead of
  silently skipping them. This is a **breaking behavior change** but desired per
  acceptance criteria. All existing scenario YAML files only request known metrics
  (except velocity_profile in hillside_complete.yaml, which this ticket adds).

## Ordering

1. Add velocity_profile to runner.py (needed before fixing compute_metrics error)
2. Fix compute_metrics ValueError behavior in runner.py
3. Update/add tests in test_scenarios.py
4. Run full test suite to verify
