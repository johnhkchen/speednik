# T-010-12 Plan: Trajectory Serialization & Metrics

## Step 1: Add velocity_profile metric to runner.py

Add `_metric_velocity_profile` function after `_metric_stuck_at` (line 174).
Add `"velocity_profile": _metric_velocity_profile` entry to `_METRIC_DISPATCH` dict.

**Verify**: Import and call `_metric_velocity_profile` manually with test data.

## Step 2: Fix compute_metrics to raise ValueError on unknown metrics

Replace the silent-skip logic in `compute_metrics` (lines 198-201):
- Change `if func is not None: result[name] = ...` to
  `if func is None: raise ValueError(...); result[name] = ...`

**Verify**: `compute_metrics(["bogus"], [], sim, True)` raises ValueError.

## Step 3: Update test_unknown_metric_ignored → test_unknown_metric_raises

Replace the existing test (line 651-658) that asserts unknown metrics are silently
skipped. New test asserts `pytest.raises(ValueError, match="Unknown metric")`.

**Verify**: `uv run pytest tests/test_scenarios.py::TestComputeMetrics::test_unknown_metric_raises -x`

## Step 4: Add missing metric unit tests

Add to TestComputeMetrics:

a. `test_death_count` — Set sim.deaths=3, assert result is 3
b. `test_stuck_at_stuck` — 120 frames at x=100.0, assert result == 100.0
c. `test_stuck_at_not_stuck` — 120 frames with x increasing, assert result is None
d. `test_stuck_at_short_trajectory` — 10 frames at constant x, spread < 2.0 still
   triggers because window = min(120, 10) = 10
e. `test_velocity_profile` — trajectory with varying x_vel, verify returned list
f. `test_empty_trajectory_metrics` — Empty trajectory for each metric type
g. `test_only_requested_metrics_computed` — Request ["max_x"], verify only "max_x"
   key in result dict

**Verify**: `uv run pytest tests/test_scenarios.py::TestComputeMetrics -x`

## Step 5: Add round-trip serialization tests

Add TestRoundTrip class after TestSaveResults:

a. `test_round_trip_basic` — Create outcomes, save_results to tmp_path, json.load,
   verify name/success/reason/frames_elapsed/wall_time_ms/metrics match
b. `test_round_trip_with_trajectory` — Save with include_trajectory=True, load,
   verify trajectory[0] has all 13 FrameRecord fields with correct values
c. `test_round_trip_null_metrics` — Verify completion_time=None and stuck_at=None
   survive JSON round-trip as null→None

**Verify**: `uv run pytest tests/test_scenarios.py::TestRoundTrip -x`

## Step 6: Run full test suite

Run `uv run pytest tests/ -x` to verify nothing is broken.
Check that hillside_complete.yaml (which requests velocity_profile) now works
correctly in integration tests.

---

## Testing Strategy

| Test Category | Count | Location |
|---------------|-------|----------|
| Metric unit tests (new) | 7 | TestComputeMetrics |
| Existing metric test fix | 1 | TestComputeMetrics |
| Round-trip serialization | 3 | TestRoundTrip (new class) |
| Existing tests (unchanged) | ~90 | Various classes |
| **Total new/changed** | **11** | |

## Commit Plan

Single commit after all changes pass: "feat: add velocity_profile metric,
unknown-metric errors, and comprehensive metric/serialization tests (T-010-12)"
