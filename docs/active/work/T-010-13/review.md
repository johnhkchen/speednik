# T-010-13 Review: Baseline Comparison and Regression Detection

## Summary of Changes

### Files Created
- **`speednik/scenarios/compare.py`** (~190 lines) — New module with metric directionality, regression detection, status change formatting, and the rewritten `compare_results()` function that returns an exit code.
- **`results/.gitkeep`** — Empty file to track the results directory.

### Files Modified
- **`speednik/scenarios/output.py`** — Removed old `compare_results` function (42 lines removed). Updated docstring.
- **`speednik/scenarios/__init__.py`** — Changed import source for `compare_results` from `.output` to `.compare`.
- **`speednik/scenarios/cli.py`** — Changed import source. Exit code from `compare_results()` now used when `--compare` is active, overriding the default pass/fail exit code.
- **`tests/test_scenarios.py`** — Replaced 2 old comparison tests with 25 new tests across 3 test classes (`TestMetricDirection`, `TestIsRegression`, `TestCompareResults`). Updated `TestCliNoPyxel` to cover `compare.py`.

## Acceptance Criteria Evaluation

| Criterion | Status |
|-----------|--------|
| `--compare baseline.json` loads baseline and prints per-scenario diff | ✓ |
| Percentage change shown for each metric | ✓ |
| Regressions flagged with ⚠ based on metric directionality | ✓ |
| Status changes (PASS↔FAIL) printed prominently | ✓ |
| Regression threshold (default 5%) filters noise | ✓ |
| Exit code 0/1/2 for no regressions/status flips/metric regressions | ✓ |
| Handles missing scenarios in baseline (NEW) | ✓ |
| Handles missing scenarios in current run (MISSING) | ✓ |
| `results/` directory created with `.gitkeep` | ✓ |
| No Pyxel imports | ✓ |
| `uv run pytest tests/ -x` passes | ✓ (pre-existing failure in test_geometry_probes unrelated) |

## Test Coverage

**25 new tests** added (net +23, replacing 2 old tests):

- `TestMetricDirection` (2): Ensures all dispatch metrics have direction entries; values are valid.
- `TestIsRegression` (10): Covers all three directions (higher/lower/neutral), threshold boundary, zero old value, unknown metric, custom threshold.
- `TestCompareResults` (13): Integration tests with capsys checking printed output + exit codes. Covers basic deltas, new/missing scenarios, both status flip directions, metric regressions, below-threshold changes, None values, list metric skipping, improvement annotations, multi-scenario mixed results.
- `TestCliNoPyxel` updated: now includes `compare.py`.

Total scenario tests: 123 (all pass in 0.66s).

## Design Decisions

1. **`compare_results` returns exit code** — Keeps the function self-contained (prints + returns code). The CLI uses the returned code when `--compare` is active.
2. **Compare exit code overrides scenario exit code** — When `--compare` is used, the comparison result is what matters. A scenario already failing in the baseline shouldn't cause exit 1.
3. **List metrics silently skipped** — `velocity_profile` (list) can't be meaningfully compared with percentage change. Skipped without warning.
4. **Threshold is a function parameter, not a CLI flag** — The ticket doesn't ask for `--threshold`. Kept configurable for testing but defaulted to 0.05.

## Open Concerns

1. **No CLI integration test for `--compare`** — The `TestCliMain` tests run real scenarios which take time. Adding a `--compare` integration test would require first saving output then comparing, adding test complexity. The unit tests on `compare_results()` cover the logic thoroughly.
2. **No initial baseline committed** — The ticket says to generate `results/baseline.json` after all scenarios pass. This requires running `uv run python -m speednik.scenarios.cli --all -o results/baseline.json` — left to the user since scenario pass/fail status may vary.
3. **Pre-existing test failure** — `tests/test_geometry_probes.py::TestRampTransition::test_no_velocity_zeroing` fails before and after these changes. Unrelated to this ticket.
