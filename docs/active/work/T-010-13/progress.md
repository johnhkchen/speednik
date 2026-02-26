# T-010-13 Progress: Baseline Comparison and Regression Detection

## Completed

### Step 1: Created `speednik/scenarios/compare.py`
- `METRIC_DIRECTION` constant with all 9 comparable metrics
- `is_regression()` function with directional threshold logic
- `_pct_change()`, `_annotation()`, `_format_val()` helpers
- `_format_status_changes()` — detects PASS↔FAIL flips
- `_format_scenario_metrics()` — per-metric diffs with annotations
- `compare_results()` — main entry point, returns exit code 0/1/2

### Step 2: Updated `output.py`
- Removed old `compare_results` function (lines 110-152)
- Updated module docstring

### Step 3: Updated `__init__.py`
- Changed `compare_results` import from `.output` to `.compare`

### Step 4: Updated `cli.py`
- Changed import source for `compare_results`
- Exit code from `compare_results()` used when `--compare` is active

### Step 5: Created `results/.gitkeep`
- Empty file to track directory in git

### Step 6: Wrote tests
- `TestMetricDirection`: 2 tests (completeness, valid values)
- `TestIsRegression`: 10 tests (all directions, thresholds, edge cases)
- `TestCompareResults`: 13 tests (replaced old 2 tests) covering:
  - Basic delta printing with annotations
  - New scenario, missing scenario
  - Status flips (PASS→FAIL exit 1, FAIL→PASS exit 0)
  - Metric regression exit 2
  - No regression exit 0
  - Below-threshold changes not flagged
  - None values, list metrics skipped
  - Improvement annotations (✓)
  - Multiple scenarios mixed
- Updated `TestCliNoPyxel` to include `compare.py`

### Step 7: Tests
- All 123 scenario tests pass
- Full suite: 343 passed, 1 pre-existing failure (test_geometry_probes unrelated)

## Deviations from Plan

None.
