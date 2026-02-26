# T-010-12 Progress: Trajectory Serialization & Metrics

## Completed

### Step 1: Add velocity_profile metric
- Added `_metric_velocity_profile` function to runner.py (returns `[r.x_vel for r in trajectory]`)
- Added `"velocity_profile": _metric_velocity_profile` to `_METRIC_DISPATCH`

### Step 2: Fix compute_metrics ValueError
- Changed `compute_metrics` to raise `ValueError` with message listing valid metrics
  when an unknown metric name is requested
- Old behavior: silently skipped unknown names

### Step 3: Update unknown metric test
- Replaced `test_unknown_metric_ignored` with `test_unknown_metric_raises_valueerror`
- New test asserts `pytest.raises(ValueError, match="Unknown metric.*'nonexistent'")`

### Step 4: Add missing metric unit tests
- `test_death_count` — verifies sim.deaths is returned
- `test_stuck_at_stuck` — 120 frames at constant x=100.0, returns 100.0
- `test_stuck_at_not_stuck` — 120 frames with increasing x, returns None
- `test_stuck_at_short_trajectory` — 10 frames at constant x, window clamps correctly
- `test_velocity_profile` — verifies list of x_vel values
- `test_empty_trajectory_metrics` — all metrics handle [] gracefully
- `test_only_requested_metrics_computed` — only requested keys in result

### Step 5: Add round-trip serialization tests
- `test_round_trip_basic` — save 2 outcomes, load, verify all top-level fields
- `test_round_trip_with_trajectory` — save with trajectory, verify all 13 FrameRecord fields
- `test_round_trip_null_metrics` — completion_time=None and stuck_at=None survive JSON

### Step 6: Run full test suite
- `uv run pytest tests/ -x`: 1079 passed, 16 skipped, 5 xfailed
- test_scenarios.py: 101 tests (up from 91), all passing

## Deviations from Plan

None. All steps executed as planned.
