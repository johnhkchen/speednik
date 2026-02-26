# T-010-13 Plan: Baseline Comparison and Regression Detection

## Step 1: Create `speednik/scenarios/compare.py` with core logic

Write the new module with:
1. `METRIC_DIRECTION` constant dict mapping all 10 metrics
2. `is_regression(metric, old_val, new_val, threshold=0.05)` function
3. `_pct_change(old_val, new_val)` helper
4. `_annotation(metric, old_val, new_val, threshold)` helper — returns `"✓ faster"`, `"⚠ regression"`, etc.
5. `_format_status_changes(current_by_name, baseline_by_name)` — detects PASS↔FAIL flips
6. `_format_scenario_metrics(name, current_metrics, baseline_metrics, threshold)` — per-metric diff lines
7. `compare_results(current, baseline_path, threshold=0.05)` — main function, prints comparison, returns exit code

**Verify**: Module imports cleanly, no Pyxel imports.

## Step 2: Update `output.py` — remove old `compare_results`

Remove the `compare_results` function (lines 110-152) and the section comment above it.

**Verify**: `output.py` still exports `print_outcome`, `print_summary`, `save_results`.

## Step 3: Update `__init__.py` — change import source

Change `compare_results` import from `.output` to `.compare`.

**Verify**: `from speednik.scenarios import compare_results` works.

## Step 4: Update `cli.py` — change import and exit code logic

1. Change import: `from speednik.scenarios.compare import compare_results`
2. Change exit logic: when `--compare` is active, use return value of `compare_results()` as exit code; otherwise keep existing 0/1 behavior.

**Verify**: CLI parses `--compare` and new exit code paths work.

## Step 5: Create `results/.gitkeep`

Create the empty file so the directory is tracked.

## Step 6: Write tests

Add to `tests/test_scenarios.py`:

### TestMetricDirection
- All metrics in `_METRIC_DISPATCH` have an entry in `METRIC_DIRECTION`
- Values are all "higher", "lower", or "neutral"

### TestIsRegression
- Higher-is-better metric: decrease beyond threshold → True
- Higher-is-better metric: decrease within threshold → False
- Higher-is-better metric: increase → False
- Lower-is-better metric: increase beyond threshold → True
- Lower-is-better metric: decrease → False
- Neutral metric → always False
- Zero old_val → no crash, returns False

### TestCompareResults (replace existing 2 tests)
- Basic delta printing with annotations
- Status changes printed at top
- PASS→FAIL gives exit code 1
- Metric regression (no status flip) gives exit code 2
- No regressions gives exit code 0
- New scenario (not in baseline) printed as "NEW"
- Missing scenario (in baseline, not in current) printed as "MISSING"
- None metric values handled gracefully
- Changes below threshold shown but not flagged
- Multiple scenarios with mixed results

### TestCompareNoPyxel
- `speednik.scenarios.compare` has no pyxel imports

## Step 7: Run tests

Run `uv run pytest tests/test_scenarios.py -x` and fix any failures.

## Testing Strategy

- **Unit tests**: `is_regression()` with all direction/threshold combos
- **Integration tests**: `compare_results()` with capsys to check printed output + exit code
- **Edge cases**: None values, zero denominators, empty baselines, new/missing scenarios
- **No Pyxel**: import check on `compare.py`
- **Full suite**: `uv run pytest tests/ -x` to ensure no regressions
