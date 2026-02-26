# Review — T-010-11: scenario-cli-entry-point

## Summary of Changes

### Files Created (3)

| File | Purpose | Lines |
|------|---------|-------|
| `speednik/scenarios/output.py` | Console output, JSON serialization, baseline comparison | ~120 |
| `speednik/scenarios/cli.py` | argparse CLI entry point, orchestration | ~70 |
| `speednik/scenarios/__main__.py` | `python -m speednik.scenarios` entry point | 4 |

### Files Modified (2)

| File | Change |
|------|--------|
| `speednik/scenarios/__init__.py` | Added re-exports for `print_outcome`, `print_summary`, `save_results`, `compare_results` |
| `tests/test_scenarios.py` | Added 22 new tests (7 test classes) |

## Acceptance Criteria Evaluation

- [x] `uv run python -m speednik.scenarios.cli scenarios/hillside_complete.yaml` runs
- [x] `--all` flag discovers and runs all scenarios in `scenarios/`
- [x] `--agent` flag overrides agent for all scenarios (also clears agent_params)
- [x] `-o` flag saves results as JSON
- [x] `--trajectory` flag includes per-frame data in JSON output
- [x] `--compare` flag loads baseline and prints comparison (placeholder — full in T-010-13)
- [x] Console output shows pass/fail, frames, wall time, key metrics per scenario
- [x] Exit code 0 on all-pass, 1 on any failure
- [x] `python -m speednik.scenarios` works as alias
- [x] No Pyxel imports (verified by test)
- [x] `uv run pytest tests/ -x` passes (1034 passed)

## Test Coverage

22 new tests added across 7 test classes:

| Class | Tests | Covers |
|-------|-------|--------|
| `TestPrintOutcome` | 5 | Console output format (pass/fail, metrics, stuck_at, frames, wall time) |
| `TestPrintSummary` | 2 | Summary line (all-pass, mixed results) |
| `TestSaveResults` | 5 | JSON serialization (basic, trajectory on/off, parent dirs, metric values) |
| `TestCompareResults` | 2 | Baseline comparison (delta output, missing baseline) |
| `TestCliMain` | 6 | CLI integration (no args, help, single, all, agent override, JSON output, trajectory) |
| `TestCliNoPyxel` | 2 | No Pyxel imports in new modules |

Total scenario test count: 69 -> 91.

**Coverage gaps:**
- No test for `--compare` flag via CLI `main()` (tested via direct `compare_results()` function call)
- No test for TTY color output (tests run in non-TTY pytest context; ANSI codes not emitted)

## Design Decisions

1. **Agent override clears agent_params**: When `--agent` overrides the agent for a scenario, the original `agent_params` (e.g., scripted timeline, spindash charge_frames) are cleared to avoid TypeError on the new agent's constructor.

2. **`main(argv)` signature**: Accepts optional argv parameter for testability — tests pass argv directly instead of monkeypatching `sys.argv`.

3. **Output to file, not directory**: `-o` takes a file path (not directory), matching the ticket examples (`-o results/run_001.json`). Parent directories are created automatically.

4. **`print_summary()` added**: Not in the original ticket but provides standard CLI summary line. Exported from `__init__.py`.

## Open Concerns

1. **Compare is minimal**: The `--compare` implementation is a placeholder per ticket. Only prints numeric metric deltas. T-010-13 will extend this with richer comparison (status changes, threshold-based regression detection).

2. **No glob expansion**: The CLI accepts explicit file paths but doesn't expand glob patterns in scenario args (e.g., `scenarios/hillside_*.yaml`). Shell glob expansion handles this on Unix. May need explicit glob support for Windows or CI where shell expansion isn't available. Low priority.

3. **Double output on `python -m speednik.scenarios`**: The `__main__.py` in the package directory gets invoked correctly. No issues observed in testing.
