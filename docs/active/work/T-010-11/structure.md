# Structure — T-010-11: scenario-cli-entry-point

## Files Created

### `speednik/scenarios/cli.py`

Main CLI orchestration module.

**Public interface:**
- `main() -> None` — Parse args, load scenarios, run, print, save, compare, exit.

**Internal flow:**
1. Build `argparse.ArgumentParser` with: `scenarios` (nargs="*"), `--all`, `--agent`, `--output`/`-o`, `--trajectory`, `--compare`
2. Validate: if no scenarios and not `--all`, print usage and exit 2
3. Convert scenario args to `list[Path]`, call `load_scenarios()`
4. For each `ScenarioDef`: optionally override agent, call `run_scenario()`, call `print_outcome()`, collect results
5. Print summary line
6. If `--output`: call `save_results(results, path, include_trajectory)`
7. If `--compare`: call `compare_results(results, baseline_path)`
8. `sys.exit(0 if all passed else 1)`

**Dependencies:** `argparse`, `sys`, `pathlib.Path`, `speednik.scenarios.loader`, `speednik.scenarios.runner`, `speednik.scenarios.output`

### `speednik/scenarios/output.py`

Output formatting and serialization module.

**Public interface:**
- `print_outcome(outcome: ScenarioOutcome) -> None` — Print one-line pass/fail to stdout with optional color.
- `save_results(results: list[ScenarioOutcome], path: Path, include_trajectory: bool = False) -> None` — Serialize outcomes to JSON file.
- `compare_results(current: list[ScenarioOutcome], baseline_path: Path) -> None` — Load baseline JSON, print metric deltas.

**Internal helpers:**
- `_is_tty() -> bool` — `sys.stdout.isatty()`
- `_colorize(text: str, color: str) -> str` — ANSI escape wrapper (green/red), no-op if not TTY
- `_outcome_to_dict(outcome: ScenarioOutcome, include_trajectory: bool) -> dict` — Dataclass to dict with optional trajectory stripping

**Dependencies:** `sys`, `json`, `pathlib.Path`, `dataclasses.asdict`, `speednik.scenarios.runner.ScenarioOutcome`

### `speednik/scenarios/__main__.py`

Entry point for `python -m speednik.scenarios`.

**Content:** Two lines — import `main` from `cli`, call it.

**Dependencies:** `speednik.scenarios.cli`

## Files Modified

### `speednik/scenarios/__init__.py`

Add re-exports for the new public symbols from `output.py`:
- `print_outcome`
- `save_results`
- `compare_results`

Also add `main` from `cli` to `__all__` (optional — the `__main__.py` imports directly).

### `tests/test_scenarios.py`

Add new test classes at the bottom:
- `TestPrintOutcome` — capture stdout, verify format for pass/fail cases
- `TestSaveResults` — write to tmp_path, read back JSON, verify structure
- `TestCompareResults` — write baseline, run comparison, capture output
- `TestCliMain` — call `main()` with sys.argv mocking, verify exit codes
- `TestCliNoPyxel` — verify no pyxel imports in cli.py, output.py, __main__.py

## Module Boundaries

```
cli.py
  ├── imports loader.load_scenarios
  ├── imports runner.run_scenario, ScenarioOutcome
  ├── imports output.print_outcome, save_results, compare_results
  └── calls sys.exit()

output.py
  ├── imports runner.ScenarioOutcome, FrameRecord (type only)
  └── imports json, dataclasses, sys, pathlib

__main__.py
  └── imports cli.main
```

No circular dependencies. `output.py` depends only on `runner.py` types. `cli.py` depends on `loader.py`, `runner.py`, and `output.py`. `__main__.py` depends only on `cli.py`.

## Component Details

### print_outcome format

```
{status}  {name:<25s}  {frames:>5d} frames  {wall_time:>7.1f}ms  {metrics}
```

Where:
- `status` = `PASS` (green) or `FAIL` (red) when TTY, plain otherwise
- `name` = scenario name, left-aligned padded to 25 chars
- `frames` = `frames_elapsed`, right-aligned 5 chars
- `wall_time` = `wall_time_ms`, 1 decimal place
- `metrics` = space-separated `key=value` pairs. Always include `max_x` if present. Include `stuck_at` if present and non-null.

### save_results JSON structure

```json
[
  {
    "name": "...",
    "success": true,
    "reason": "...",
    "frames_elapsed": 1847,
    "wall_time_ms": 42.3,
    "metrics": { ... },
    "trajectory": [ ... ]  // only if include_trajectory=True
  },
  ...
]
```

### compare_results output format

```
hillside_complete:
  max_x:           3200.0 -> 3200.0 ( 0.0%)
  average_speed:      4.2 ->    4.8 (+14.3%)
```

For each scenario present in both current and baseline results, print each shared metric with old, new, and percentage delta.

### Summary line format

```
{n} scenarios: {pass_count} passed, {fail_count} failed
```

Colorize pass count green, fail count red if non-zero, on TTY.
