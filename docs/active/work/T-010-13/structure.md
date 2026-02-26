# T-010-13 Structure: Baseline Comparison and Regression Detection

## Files Created

### `speednik/scenarios/compare.py`
New module containing all comparison and regression detection logic.

**Constants:**
```python
METRIC_DIRECTION: dict[str, str]  # metric_name → "higher" | "lower" | "neutral"
```

**Functions:**
```python
def is_regression(metric: str, old_val: float, new_val: float, threshold: float = 0.05) -> bool
    """Check if a metric change is a regression beyond threshold."""

def compare_results(
    current: list[ScenarioOutcome],
    baseline_path: Path | str,
    threshold: float = 0.05,
) -> int
    """Load baseline, print comparison, return exit code (0/1/2)."""
```

**Internal helpers:**
```python
def _format_status_changes(current_by_name, baseline_by_name) -> tuple[list[str], bool]
    """Find and format status flips. Returns (lines, has_pass_to_fail)."""

def _format_scenario_metrics(name, current_metrics, baseline_metrics, threshold) -> list[str]
    """Format per-metric comparison for one scenario."""

def _pct_change(old_val, new_val) -> float | None
    """Compute percentage change, handling zero denominators."""

def _annotation(metric, old_val, new_val, threshold) -> str
    """Return annotation string: '✓ faster', '⚠ regression', etc."""
```

### `results/.gitkeep`
Empty file to ensure the directory is tracked by git.

## Files Modified

### `speednik/scenarios/output.py`
- **Remove**: `compare_results` function (lines 110-152)
- Keep: `print_outcome`, `print_summary`, `save_results`, color helpers

### `speednik/scenarios/cli.py`
- **Change import**: `compare_results` from `compare` instead of `output`
- **Change exit logic**: When `--compare` is used, use the return value of `compare_results` as the exit code instead of the pass/fail check

### `speednik/scenarios/__init__.py`
- **Change import source**: `compare_results` from `.compare` instead of `.output`

### `tests/test_scenarios.py`
- **Update imports** in `TestCompareResults`: import from `speednik.scenarios.compare`
- **Add tests**: ~15 new test methods covering:
  - `METRIC_DIRECTION` completeness
  - `is_regression()` for each direction type + threshold edge cases
  - `compare_results()` output formatting
  - Status change detection (PASS→FAIL, FAIL→PASS)
  - Exit codes (0, 1, 2)
  - New scenario (in current but not baseline)
  - Missing scenario (in baseline but not current)
  - None-value metric handling
  - Threshold filtering (change < 5% not flagged)

## Module Boundaries

```
cli.py ──→ compare.py (compare_results)
       ──→ output.py  (print_outcome, print_summary, save_results)
       ──→ runner.py   (run_scenario)
       ──→ loader.py   (load_scenarios)

compare.py ──→ runner.py (ScenarioOutcome type)
```

`compare.py` reads JSON directly (via `json.load`), does not depend on `output.py`.

## Public Interface

The only new public symbol: nothing new — `compare_results` already exists in `__all__`. Its signature changes from `-> None` to `-> int`, and it gains a `threshold` parameter.

## Directory Structure After Changes

```
speednik/scenarios/
├── __init__.py      (modified: import source change)
├── __main__.py      (unchanged)
├── cli.py           (modified: import + exit code logic)
├── compare.py       (NEW)
├── conditions.py    (unchanged)
├── loader.py        (unchanged)
├── output.py        (modified: remove compare_results)
└── runner.py        (unchanged)

results/
└── .gitkeep         (NEW)
```
