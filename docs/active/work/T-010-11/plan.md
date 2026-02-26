# Plan — T-010-11: scenario-cli-entry-point

## Step 1: Create `speednik/scenarios/output.py`

Implement the three public functions:
- `print_outcome(outcome)` — TTY-aware one-line output with ANSI colors
- `save_results(results, path, include_trajectory)` — JSON serialization
- `compare_results(current, baseline_path)` — load baseline, print metric deltas

Internal helpers: `_is_tty()`, `_colorize()`, `_outcome_to_dict()`.

**Verify:** Unit tests for output formatting (Step 5).

## Step 2: Create `speednik/scenarios/cli.py`

Implement `main()`:
- argparse setup with all five flags
- Scenario loading via `load_scenarios()`
- Agent override loop
- Result collection and printing
- Summary line
- JSON output and comparison
- Exit code (0 or 1)

**Verify:** Can run `uv run python speednik/scenarios/cli.py --help` to verify argparse.

## Step 3: Create `speednik/scenarios/__main__.py`

Two-line file: import main, call it.

**Verify:** `uv run python -m speednik.scenarios --help` works.

## Step 4: Update `speednik/scenarios/__init__.py`

Add re-exports for `print_outcome`, `save_results`, `compare_results` from `output.py`.

**Verify:** `from speednik.scenarios import print_outcome` works.

## Step 5: Write tests in `tests/test_scenarios.py`

Add at the bottom of the existing test file:

### TestPrintOutcome
- `test_print_pass` — create a passing ScenarioOutcome, capture stdout, verify "PASS" and name appear
- `test_print_fail` — create a failing outcome, verify "FAIL" appears
- `test_print_includes_metrics` — verify max_x shown in output
- `test_print_includes_stuck_at` — verify stuck_at shown when present

### TestSaveResults
- `test_save_basic` — save to tmp_path, read back, verify JSON list structure
- `test_save_without_trajectory` — verify trajectory key absent by default
- `test_save_with_trajectory` — verify trajectory key present
- `test_save_creates_parent_dirs` — save to nested path, verify dirs created

### TestCompareResults
- `test_compare_prints_deltas` — write baseline JSON, run comparison, capture output, verify delta format

### TestCliMain
- `test_cli_all_pass_exit_0` — monkeypatch sys.argv with a short scenario, catch SystemExit(0)
- `test_cli_no_args_exit_2` — no scenarios, no --all, verify exit 2
- `test_cli_agent_override` — verify --agent flag changes the agent used

### TestCliNoPyxel
- `test_cli_no_pyxel` — read source of cli.py, output.py, __main__.py; assert no pyxel imports

## Step 6: Run full test suite

Run `uv run pytest tests/ -x` and fix any failures.

## Testing Strategy

- **Unit tests**: Output formatting functions tested with synthetic ScenarioOutcome objects (no simulation needed — fast).
- **Integration tests**: CLI main() tested with monkeypatched sys.argv against real short scenarios (30-60 frames).
- **No-Pyxel test**: Source text scan, consistent with existing pattern in test_scenarios.py.
- All tests added to the existing `tests/test_scenarios.py` to keep scenario-related tests together.
