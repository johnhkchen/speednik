# Plan — T-011-06 naive-player-regression-suite

## Steps

### Step 1: Create tests/test_regression.py with imports and constants

Write the file header, imports, and constant definitions:
- STAGES dict (stage → width, max_frames)
- STRATEGIES dict (name → factory function)
- X_THRESHOLD_FRACTION
- MAX_DEATHS dict

Verify: File parses without import errors.

### Step 2: Add data structures

Add `RegressionSnapshot` and `RegressionResult` dataclasses.

Verify: Import the module, instantiate both dataclasses.

### Step 3: Implement _run_regression runner

Write the unified sim + camera loop:
1. Create sim and camera
2. Instantiate strategy
3. Frame loop: sim_step + camera_update + snapshot capture
4. Build CameraTrajectory
5. Return RegressionResult

Verify: Call `_run_regression("hillside", "hold_right")` and inspect result.

### Step 4: Add cache and parameterized test class skeleton

Add `_RESULT_CACHE`, `_get_result()`, parameter lists, and the `TestRegression`
class with all 5 test methods as stubs.

Verify: `pytest --collect-only tests/test_regression.py` shows 45 test items
(9 combos × 5 tests).

### Step 5: Implement test_invariants

Call `check_invariants`, filter for error severity, assert 0 errors.
Include violation details in assertion message.

Verify: Run test_invariants for hillside/hold_right.

### Step 6: Implement test_camera_no_oscillation

Import `check_oscillation` from test_camera_stability.
Check both axes, assert no violations.

Verify: Run test_camera_no_oscillation for hillside/hold_right.

### Step 7: Implement test_forward_progress

Assert `result.max_x >= STAGES[stage]["width"] * X_THRESHOLD_FRACTION`.

Verify: Run for all 9 combos.

### Step 8: Implement test_deaths_within_bounds

Assert `result.deaths <= MAX_DEATHS[stage][strategy]`.

Verify: Run for all 9 combos.

### Step 9: Implement test_results_logged

Print summary per combo: stage, strategy, max_x, rings, deaths, goal, frames.
No assertion on content — just verify it prints without error.

Verify: Run with `-s` flag to see output.

### Step 10: Full test run

Run `uv run pytest tests/test_regression.py -x -v` and verify all 45 tests pass.
Fix any failures.

## Testing Strategy

- **Unit verification**: Each step verified independently via targeted pytest invocation.
- **Integration**: Step 10 runs the full matrix.
- **Regression gate**: The file IS the regression gate — if it passes, invariants
  and camera stability are confirmed across all combos.
- **No new unit tests needed**: The test file itself is the deliverable.

## Risk Mitigation

- **Slow test**: 9 combos × 4000-6000 frames each. But caching means each combo
  runs once regardless of how many test methods check it. Expected wall time ~30-60s.
- **Invariant false positives**: Some combos (e.g., skybridge/spindash) may trigger
  position_x_beyond_right when player flies off-map via springs. These are
  legitimate warnings. We filter for `severity=="error"` only.
- **Camera import coupling**: If test_camera_stability changes its helper signatures,
  this test breaks. Acceptable — both are test files in the same project.
