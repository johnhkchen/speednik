# Design — T-010-11: scenario-cli-entry-point

## Problem

Need a CLI entry point that runs scenario YAML files, prints pass/fail results, saves JSON output, and supports agent override and baseline comparison. Must work with `python -m speednik.scenarios.cli` and `python -m speednik.scenarios`.

## Approach A: Monolithic cli.py (Rejected)

Put all logic — argument parsing, output formatting, JSON serialization, comparison — in a single `cli.py` file.

**Pro**: Single file, simple imports.
**Con**: Mixes presentation (TTY color, formatting), serialization (JSON), and orchestration (argparse, scenario loop). Hard to test output formatting in isolation. Violates the module-per-concern pattern established by `loader.py`, `conditions.py`, `runner.py`.

## Approach B: Split output.py + cli.py (Chosen)

Follow the ticket's suggested file layout:
- `cli.py` — argparse, orchestration loop, exit code logic
- `output.py` — `print_outcome()`, `save_results()`, `compare_results()` (presentation + serialization)
- `__main__.py` — one-liner entry point

**Pro**: Testable output formatting. `output.py` functions can be imported independently. Consistent with existing module-per-concern pattern. Ticket explicitly calls for this split.
**Con**: One more file. Acceptable — the three functions have distinct responsibilities.

### Rationale

The ticket prescribes this split (`cli.py`, `output.py`, `__main__.py`). The scenario subsystem already has four files with clean separation. Adding two more follows the established pattern. Output formatting and JSON serialization are logically distinct from CLI orchestration.

## Design Decisions

### 1. Console Output Format

Use the format from the ticket with minor refinement:

```
PASS  hillside_complete     1847 frames  42.3ms  max_x=3200.5
FAIL  hillside_hold_right   3600 frames  98.1ms  max_x=1456.2  stuck_at=1456.2
```

- Status: `PASS` or `FAIL`, colorized on TTY (green/red)
- Name: left-padded to align columns
- Frames elapsed, wall time (1 decimal), key metrics
- Metrics shown: always `max_x` from outcome metrics (if available), plus `stuck_at` if non-null. These are the two most informative for a quick scan.

TTY detection: `sys.stdout.isatty()`. Use ANSI escape codes directly — no external dependency.

### 2. JSON Serialization

`ScenarioOutcome` and `FrameRecord` are dataclasses. Use `dataclasses.asdict()` for recursive conversion. Strip `trajectory` key from each outcome dict unless `--trajectory` is passed. Write a list of outcome dicts to the output path.

Output path is a file path (not a directory — the ticket shows `-o results/run_001.json`). Create parent directories if needed.

### 3. Comparison (Placeholder)

The ticket says `--compare` is a placeholder for T-010-13. Implement a minimal version:
- Load baseline JSON
- For each scenario name that appears in both current and baseline, print metric deltas with percentage change
- This is enough to be useful now and will be replaced/extended by T-010-13

### 4. Exit Code

`sys.exit(0)` if all outcomes have `success=True`, `sys.exit(1)` otherwise. Straightforward.

### 5. Scenario Loading Bridge

The CLI receives `args.scenarios` (list of strings) and `args.all` (bool). Convert scenario strings to Paths, pass to `load_scenarios(paths, run_all=args.all)`. If neither scenarios nor `--all` given, print help and exit.

### 6. Agent Override

`ScenarioDef.agent` is a mutable string attribute. Set it before calling `run_scenario()`, as the ticket shows. No copy needed — the def is not reused.

### 7. __main__.py

```python
from speednik.scenarios.cli import main
main()
```

This makes `python -m speednik.scenarios` work.

### 8. Summary Line

After all scenarios, print a summary line:

```
5 scenarios: 4 passed, 1 failed
```

The ticket doesn't explicitly require this but it's standard CLI behavior and trivially implemented.

## Rejected Alternatives

### Click/Typer instead of argparse
Overkill for 5 flags. Would add a dependency. argparse is stdlib and sufficient.

### Rich for terminal output
Overkill. ANSI escape codes for green/red are 10 lines of code. No dependency needed.

### Streaming output (print each outcome as it completes)
Already the natural implementation — the loop prints after each `run_scenario()` call. No special streaming mechanism needed.

## Integration Points

- `speednik/scenarios/loader.py::load_scenarios()` — scenario loading
- `speednik/scenarios/runner.py::run_scenario()` — execution
- `speednik/scenarios/runner.py::ScenarioOutcome` — result type
- `speednik/scenarios/__init__.py` — needs to re-export new symbols from `output.py`

## Test Strategy

- Unit tests for `print_outcome()` — capture stdout, verify format
- Unit tests for `save_results()` — write to tmp_path, verify JSON structure
- Unit test for `compare_results()` — mock baseline, verify delta output
- Integration test: invoke `cli.main()` with args, verify exit code
- No-Pyxel assertion for new modules
