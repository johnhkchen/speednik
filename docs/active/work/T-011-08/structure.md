# T-011-08 Structure: Extract Shared Code from Tests

## File Operations

### New Files

#### `speednik/grids.py`
- **Content:** Complete copy of `tests/grids.py` (380 lines).
- **Public API:** `FILL_DEPTH`, `build_flat`, `build_gap`, `build_slope`, `build_ramp`, `build_loop`.
- **Internal:** `_wrap`, `_flat_tile`, `_fill_below`, `_slope_height_array`.
- **Imports:** `math`, `typing.Optional`, `speednik.terrain` (FULL, SURFACE_LOOP, TILE_SIZE, TOP_ONLY, Tile, TileLookup).
- **Docstring:** Update from "Synthetic tile-grid builders for physics tests" to
  "Synthetic tile-grid builders for physics scenarios and dev park."

#### `speednik/strategies.py`
- **Content:** Complete copy of `tests/harness.py` (271 lines).
- **Public API:** `Strategy`, `FrameSnapshot`, `ScenarioResult`, `run_scenario`,
  `run_on_stage`, `idle`, `hold_right`, `hold_left`, `hold_right_jump`,
  `spindash_right`, `scripted`.
- **Internal:** `_capture_snapshot`.
- **Imports:** `dataclasses`, `typing.Callable`, `speednik.level`, `speednik.physics`,
  `speednik.player`, `speednik.terrain`.
- **Docstring:** Update from "tests/harness.py — Scenario runner..." to
  "speednik/strategies.py — Strategy primitives and scenario runner."

### Modified Files

#### `tests/grids.py` (380 lines → ~3 lines)
Replace entire content with re-export shim:
```python
"""Re-export shim — canonical location is speednik.grids."""
from speednik.grids import *  # noqa: F401,F403
```

#### `tests/harness.py` (271 lines → ~3 lines)
Replace entire content with re-export shim:
```python
"""Re-export shim — canonical location is speednik.strategies."""
from speednik.strategies import *  # noqa: F401,F403
```

#### `speednik/devpark.py` (13 import statements changed)
All lazy imports updated — module path changes only, imported names unchanged:

| Line | Old | New |
|------|-----|-----|
| 116 | `from tests.harness import ...` | `from speednik.strategies import ...` |
| 169 | `from tests.grids import build_ramp` | `from speednik.grids import build_ramp` |
| 170 | `from tests.harness import ...` | `from speednik.strategies import ...` |
| 187 | `from tests.grids import build_ramp` | `from speednik.grids import build_ramp` |
| 188 | `from tests.harness import ...` | `from speednik.strategies import ...` |
| 205 | `from tests.grids import build_loop` | `from speednik.grids import build_loop` |
| 206 | `from tests.harness import ...` | `from speednik.strategies import ...` |
| 221 | `from tests.grids import build_loop` | `from speednik.grids import build_loop` |
| 222 | `from tests.harness import ...` | `from speednik.strategies import ...` |
| 241 | `from tests.grids import build_gap` | `from speednik.grids import build_gap` |
| 242 | `from tests.harness import ...` | `from speednik.strategies import ...` |
| 259 | `from tests.harness import hold_right` | `from speednik.strategies import hold_right` |
| 280 | `from tests.harness import ...` | `from speednik.strategies import ...` |

### Unchanged Files

- All 8 test files (`test_grids.py`, `test_harness.py`, `test_elementals.py`,
  `test_levels.py`, `test_simulation.py`, `test_camera_stability.py`,
  `test_invariants.py`, `test_devpark.py`) — re-export shims preserve their imports.
- `speednik/agents/` — no changes needed; no import dependency on strategies.
- `tests/__init__.py` — remains empty.

## Module Boundaries

```
speednik/
  grids.py          ← canonical: grid builders (no Pyxel)
  strategies.py     ← canonical: strategies, runners, result types (no Pyxel)
  devpark.py        ← consumer: imports from speednik.grids + speednik.strategies
  agents/           ← independent: observation-based agents (no overlap)

tests/
  grids.py          ← shim: re-exports from speednik.grids
  harness.py        ← shim: re-exports from speednik.strategies
  test_*.py         ← unchanged: import from tests.grids / tests.harness
```

## Ordering

1. Create `speednik/grids.py` (no dependencies on other new files).
2. Create `speednik/strategies.py` (no dependencies on other new files).
3. Convert `tests/grids.py` to shim (depends on step 1).
4. Convert `tests/harness.py` to shim (depends on step 2).
5. Update `speednik/devpark.py` imports (depends on steps 1-2).

Steps 1-2 can be done in parallel. Steps 3-5 can be done in parallel after 1-2.
