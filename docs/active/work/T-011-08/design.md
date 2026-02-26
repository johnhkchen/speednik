# T-011-08 Design: Extract Shared Code from Tests

## Decision Summary

**Move code + re-export shims.** Create `speednik/grids.py` and `speednik/strategies.py`
as the canonical locations. Convert `tests/grids.py` and `tests/harness.py` to thin
re-export shims (`from speednik.X import *`) so existing test imports work unchanged.

## Options Evaluated

### Option A: Move code, update all imports everywhere

Move `tests/grids.py` → `speednik/grids.py` and strategy code from `tests/harness.py` →
`speednik/strategies.py`. Delete old files. Update all 8 test files + devpark.py to import
from new locations.

**Pros:** Clean — no indirection, no shim files, single source of truth.
**Cons:** High churn — 8 test files need import changes. Risk of merge conflicts with
other in-flight tickets that touch test files.

### Option B: Move code, keep re-export shims (CHOSEN)

Same move, but `tests/grids.py` and `tests/harness.py` become one-line re-export shims:
```python
from speednik.grids import *  # noqa: F401,F403
```

**Pros:**
- Zero changes needed in test files — all existing `from tests.grids import X` continue to work.
- Minimal merge conflict surface — only devpark.py and 2 shim files change.
- Shims are explicit about the redirection — easy to grep and remove later.
- Matches ticket recommendation ("prefer the re-export approach to minimize churn").

**Cons:**
- Two extra files that are pure indirection.
- `import *` is slightly impure, but acceptable for thin shims.

### Option C: Symlinks or sys.path manipulation

Make `speednik/grids.py` a symlink to `tests/grids.py`, or add `tests/` to runtime sys.path.

**Rejected:** Fragile across platforms. sys.path manipulation is a hack. Symlinks break on
Windows and in some packaging contexts.

### Option D: Keep code in tests/, add tests/ to package

Configure `tests/` as a runtime package in pyproject.toml.

**Rejected:** Tests should not be shipped as part of the runtime package. This defeats the
purpose of separating test code from production code.

## Decision: Option B

Re-export shims minimize churn while fixing the runtime import error. The ticket explicitly
recommends this approach. The shims can be removed in a future cleanup ticket if desired.

## Module Naming

- `speednik/grids.py` — All grid builders and helpers. Name matches `tests/grids.py`.
- `speednik/strategies.py` — All strategy functions, type alias, dataclasses, runners.
  Named "strategies" rather than "harness" because:
  - "harness" implies test infrastructure; these are now production-path code.
  - The module contains strategy factories, strategy runners, and strategy result types.
  - Matches the ticket specification.

## What Moves Where

### `tests/grids.py` → `speednik/grids.py` (complete move)

Everything moves: constant `FILL_DEPTH`, 4 internal helpers (`_wrap`, `_flat_tile`,
`_fill_below`, `_slope_height_array`), 5 public builders (`build_flat`, `build_gap`,
`build_slope`, `build_ramp`, `build_loop`). No changes to signatures or behavior.

### `tests/harness.py` → `speednik/strategies.py` (complete move)

Everything moves: `Strategy` type alias, `FrameSnapshot` and `ScenarioResult` dataclasses,
`_capture_snapshot` helper, `run_scenario` and `run_on_stage` runners, all 6 strategy
factories. No changes to signatures or behavior.

## Agent/Strategy Boundary

The agents (`speednik/agents/`) and strategies (`speednik/strategies.py`) serve different
interfaces:
- **Agents:** `act(obs: np.ndarray) -> int` — observation-based, for RL/Gymnasium.
- **Strategies:** `(frame: int, player: Player) -> InputState` — direct-control, for
  headless testing and dev park visualization.

No code sharing between them. Both are needed. No conflict.

## Import Style in devpark.py

Convert lazy imports to point at new module. Keep them lazy (inside functions) since devpark
is only used in debug mode and the lazy pattern avoids importing simulation code at game
startup when dev park isn't active. This is the existing pattern and there's no reason to
change it.

## Re-export Shim Pattern

```python
# tests/grids.py
"""Re-export shim — canonical location is speednik.grids."""
from speednik.grids import *  # noqa: F401,F403
```

The `# noqa` comments suppress flake8 warnings for unused imports and wildcard imports.
Include the module docstring to make the indirection discoverable.
