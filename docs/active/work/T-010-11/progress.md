# Progress — T-010-11: scenario-cli-entry-point

## Completed

### Step 1: Created `speednik/scenarios/output.py`
- `print_outcome()` — one-line pass/fail with TTY-aware ANSI colors (green/red), frames, wall time, key metrics (max_x, stuck_at)
- `print_summary()` — summary line with pass/fail counts
- `save_results()` — JSON serialization via `dataclasses.asdict()`, optional trajectory inclusion, parent directory creation
- `compare_results()` — loads baseline JSON, prints metric deltas with percentage change
- Internal helpers: `_is_tty()`, `_colorize()`, `_outcome_to_dict()`

### Step 2: Created `speednik/scenarios/cli.py`
- `main(argv=None)` — full argparse setup with all 5 flags (scenarios, --all, --agent, --output/-o, --trajectory, --compare)
- Validates that scenarios or --all must be specified (exit 2 otherwise)
- Agent override clears `agent_params` to avoid incompatible kwargs (caught by test)
- Exit code 0 if all pass, 1 if any fail

### Step 3: Created `speednik/scenarios/__main__.py`
- Two-line entry point: imports and calls `main()` from `cli.py`
- `python -m speednik.scenarios` works as alias

### Step 4: Updated `speednik/scenarios/__init__.py`
- Added re-exports for `print_outcome`, `print_summary`, `save_results`, `compare_results`

### Step 5: Added tests to `tests/test_scenarios.py`
- `TestPrintOutcome` — 5 tests (pass, fail, metrics, stuck_at, frames/wall_time)
- `TestPrintSummary` — 2 tests (all pass, mixed)
- `TestSaveResults` — 5 tests (basic, without trajectory, with trajectory, parent dirs, metrics)
- `TestCompareResults` — 2 tests (deltas, no baseline)
- `TestCliMain` — 6 tests (no args, help, single scenario, all, agent override, output json, trajectory)
- `TestCliNoPyxel` — 2 tests (cli/output modules, __main__.py)

### Step 6: Ran full test suite
- 1034 passed, 5 xfailed, 9 warnings (all pre-existing)
- 91 scenario-specific tests pass (was 69, added 22)

## Deviations from Plan

1. **Agent override clears agent_params**: Discovered during testing that overriding agent name while keeping the original scenario's agent_params causes TypeError (e.g., HoldRightAgent doesn't accept `timeline` kwargs). Fixed by setting `agent_params = None` when `--agent` is used.

2. **Added `print_summary()`**: Not in the original ticket but a natural companion to `print_outcome()`. Provides the summary line at the end of a run.

## Remaining

None — all steps complete.
