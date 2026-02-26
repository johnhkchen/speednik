# T-010-13 Design: Baseline Comparison and Regression Detection

## Decision 1: Where to Put Comparison Logic

### Option A: Extend `output.py` (in-place)
Add `METRIC_DIRECTION`, `is_regression()`, and rewrite `compare_results()` in the existing file.

### Option B: New `compare.py` module (ticket recommends)
The ticket specifies `speednik/scenarios/compare.py`. Separating comparison logic from output/serialization keeps each file focused.

**Decision: Option B — `compare.py`**
The ticket explicitly names this file. Comparison logic (directionality, thresholds, structured results) is conceptually distinct from basic output formatting. Move `compare_results` out of `output.py` into `compare.py`. Update imports in `cli.py` and `__init__.py`.

## Decision 2: Return Type of `compare_results`

### Option A: Return structured dataclass, let CLI format
A `ComparisonResult` dataclass with status changes, metric deltas, and regression flags. CLI formats and prints.

### Option B: Return an exit code integer
Simple — function prints and returns 0/1/2.

### Option C: Return exit code + print internally
Function handles both printing and exit code computation.

**Decision: Option C — return int exit code, print internally**
The ticket's comparison output is console-oriented (human-readable diff). Splitting formatting from the function that walks the data would duplicate iteration logic. Return the exit code so `cli.py` can use it. If structured results are needed later, we can refactor.

## Decision 3: Exit Code Interaction with Scenario Pass/Fail

Current behavior: exit 0 if all scenarios pass, exit 1 if any fail.
Ticket wants: exit 0 (no regressions), exit 1 (status flip PASS→FAIL), exit 2 (metric regressions).

These two concerns overlap when `--compare` is used. Options:

### Option A: Compare exit code overrides scenario exit code
When `--compare` is active, the comparison result determines the exit code entirely.

### Option B: Use max(scenario_exit, compare_exit)
Combine both signals.

**Decision: Option A — compare overrides when active**
The purpose of `--compare` is regression testing. When running with `--compare`, the user cares about whether things regressed vs the baseline, not whether scenarios pass/fail in absolute terms (the baseline captures that context). A scenario that was already failing in the baseline shouldn't cause exit 1.

## Decision 4: Handling Non-Comparable Metrics

Metrics like `velocity_profile` (a list) and `None` values (completion_time when failed) can't be meaningfully compared with percentage change.

**Decision**: Skip list-type metrics silently. For `None` values: if both are None, show "None → None"; if one is None, show the transition without percentage; flag None→value or value→None as noteworthy but not a regression.

## Decision 5: Formatting

The ticket provides a specific output format with aligned columns and emoji annotations. Follow it closely:
- `✓` for improvements above threshold
- `⚠` for regressions above threshold
- Status changes section at the top, bold/prominent
- Per-scenario metric diffs below
- Pad metric names for alignment within each scenario

## Rejected Approaches

1. **Structured JSON comparison output**: Overengineering for this ticket. The purpose is human-readable CLI output.
2. **Configurable threshold via CLI flag**: Ticket says "default 5%" but doesn't ask for a `--threshold` flag. Keep it as a function parameter for testability but don't wire to CLI.
3. **Separate baseline management commands** (save, load, diff): Out of scope. The baseline is just a JSON file from `--output`.

## Summary

- New file: `speednik/scenarios/compare.py`
- Contains: `METRIC_DIRECTION`, `is_regression()`, `compare_results()` → returns exit code int
- `compare_results` prints status changes header, then per-scenario metric diffs
- Remove `compare_results` from `output.py`
- CLI uses returned exit code when `--compare` is active
- Create `results/` with `.gitkeep`
- Test file: extend `tests/test_scenarios.py` with comprehensive comparison tests
