# T-010-13 Research: Baseline Comparison and Regression Detection

## Existing Codebase Map

### Core Files

**`speednik/scenarios/output.py`** (152 lines)
- Console output: `print_outcome()`, `print_summary()` — one-line pass/fail per scenario
- JSON serialization: `_outcome_to_dict()`, `save_results()` — writes list of outcome dicts
- Comparison: `compare_results(current, baseline_path)` — exists but **incomplete**
- Color helpers: `_is_tty()`, `_colorize()` with `_GREEN`, `_RED`, `_RESET`

**`speednik/scenarios/cli.py`** (78 lines)
- `main(argv)` — argparse-based CLI
- `--compare` flag already defined (line 42) and wired (line 68-69)
- Exit code: currently 0 if all pass, 1 if any fail — comparison does NOT affect exit code
- Flow: parse args → load scenarios → run each → print outcomes → print summary → save JSON → compare → exit

**`speednik/scenarios/runner.py`** (302 lines)
- `ScenarioOutcome` dataclass: name, success, reason, frames_elapsed, metrics, trajectory, wall_time_ms
- `FrameRecord` dataclass: 13 fields per frame
- `_METRIC_DISPATCH`: 10 metrics (completion_time, max_x, rings_collected, death_count, total_reward, average_speed, peak_speed, time_on_ground, stuck_at, velocity_profile)
- `compute_metrics()` — dispatches to individual metric functions
- `run_scenario()` — full execution engine

**`speednik/scenarios/__init__.py`** — re-exports `compare_results` already in `__all__`

### Current `compare_results` Implementation (output.py:110-152)

The function exists but is minimal:
- Loads baseline JSON, indexes by scenario name
- For missing baselines: prints "(no baseline)"
- For shared metrics: prints `key  old_val -> new_val (+X.X%)`
- Returns `None` — print-only, no structured result
- **Missing**: regression detection, metric directionality, threshold filtering, status change detection, exit code influence, handling of missing scenarios in current run, annotation symbols (✓/⚠)

### JSON Output Format (from save_results)

Array of dicts, each with:
```json
{"name": "...", "success": true, "reason": "...", "frames_elapsed": 1847,
 "metrics": {"max_x": 3200.5, ...}, "wall_time_ms": 42.3}
```
Trajectory omitted by default. This is the format `--compare` reads as baseline.

### Test Coverage (tests/test_scenarios.py)

- `TestCompareResults` (2 tests): basic delta printing, missing baseline scenario
- `TestCliMain` (7 tests): no args, help, single scenario, --all, --agent, -o JSON, --trajectory
- `_make_outcome()` helper: creates minimal `ScenarioOutcome` for output tests
- No tests for: regression detection, threshold, status flips, exit code from compare, directional annotations

### results/ Directory

Does not exist. Ticket requires creating it with `.gitkeep`.

### Dependencies

- T-010-12 (trajectory serialization and metrics) — phase: done
- The JSON format, metric names, and `ScenarioOutcome` are all stable

## Key Findings

1. **`--compare` flag and `compare_results` already exist** — this is an enhancement, not greenfield
2. **`compare_results` returns `None`** — it cannot influence CLI exit code currently
3. **Exit code logic in `cli.py`** is simple: `sys.exit(0 if all pass else 1)` — compare has no effect
4. **Metric directionality is not encoded anywhere** — must be added as a constant
5. **The ticket defines three exit codes** (0=clean, 1=status flip, 2=metric regression) which conflicts with current behavior (0=all pass, 1=any fail). The compare exit codes should take priority when `--compare` is used.
6. **No `results/` directory** — needs creation with `.gitkeep`

## Constraints

- No Pyxel imports in any scenarios module
- Must handle missing scenarios in both directions (new in current, missing from current)
- Default regression threshold: 5%
- velocity_profile metric should be excluded from comparison (list, not comparable)
- Integer metrics (completion_time, rings_collected, death_count) need proper formatting
