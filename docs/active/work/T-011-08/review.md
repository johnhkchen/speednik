# T-011-08 Review: Extract Shared Code from Tests

## Summary

Moved shared code out of `tests/` into `speednik/` to fix `ModuleNotFoundError` when
running devpark outside of pytest. Created two new production modules and converted the
original test files to re-export shims.

## Files Changed

### Created (2)
| File | Lines | Content |
|------|-------|---------|
| `speednik/grids.py` | 380 | Grid builders: `build_flat`, `build_gap`, `build_slope`, `build_ramp`, `build_loop` + helpers |
| `speednik/strategies.py` | 271 | Strategy factories, `FrameSnapshot`, `ScenarioResult`, `run_scenario`, `run_on_stage` |

### Modified (3)
| File | Change |
|------|--------|
| `tests/grids.py` | 380 → 2 lines: re-export shim (`from speednik.grids import *`) |
| `tests/harness.py` | 271 → 2 lines: re-export shim (`from speednik.strategies import *`) |
| `speednik/devpark.py` | 13 import paths changed (`tests.grids`/`tests.harness` → `speednik.grids`/`speednik.strategies`) |

### Unchanged
- All 8 test files that import from `tests.grids`/`tests.harness` — work via re-export shims.
- `speednik/agents/` — independent, no overlap to resolve.
- `tests/__init__.py` — remains empty.

## Acceptance Criteria Status

- [x] `speednik/grids.py` contains all grid builders, importable at runtime
- [x] `speednik/strategies.py` contains all strategy functions and runner
- [x] `speednik/devpark.py` imports from `speednik.grids` and `speednik.strategies`
- [x] Dev park launches without `ModuleNotFoundError` (verified via `uv run python -c`)
- [x] `tests/grids.py` and `tests/harness.py` re-export from new locations
- [x] All existing test files pass without import changes (re-export shims work)
- [x] No duplicate code between strategies.py and agents/ (different interfaces, no sharing)
- [x] `uv run pytest tests/ -x` passes (1212 passed, 16 skipped, 5 xfailed)
- [x] Runtime import verification passes outside pytest context

## Test Coverage

- **Existing tests:** 1212 passed. No new tests were needed — this is a pure move refactoring.
- **Grid builders:** Covered by `test_grids.py` (27 tests) and `test_elementals.py` (32 tests).
- **Strategies:** Covered by `test_harness.py` (20 tests), `test_levels.py`, `test_simulation.py`,
  `test_camera_stability.py`, `test_elementals.py`.
- **Devpark integration:** Covered by `test_devpark.py` (38 tests).
- **Re-export shims:** Implicitly verified — all tests import via `tests.grids`/`tests.harness`
  and pass, confirming the shims work.

## Open Concerns

1. **Re-export shims are permanent indirection.** The `tests/grids.py` and `tests/harness.py`
   shims exist solely to avoid churn in 8 test files. A future cleanup could update all test
   imports to point at `speednik.grids`/`speednik.strategies` directly and delete the shims.
   Low priority — the shims are 2 lines each and have zero maintenance burden.

2. **Agent/strategy functional overlap is by design.** `SpindashAgent`, `JumpRunnerAgent`,
   etc. implement the same behavioral logic as the strategy factories but with a different
   interface (observation vectors vs. Player objects). This is intentional — agents serve the
   RL/Gymnasium interface, strategies serve headless testing and dev park. No code sharing is
   practical given the interface difference.

3. **`import *` in shims.** The wildcard import is slightly impure but acceptable for thin
   shims whose sole purpose is re-exporting. The `# noqa: F401,F403` comments suppress linter
   warnings.

## Risk Assessment

**Low risk.** Pure move refactoring with no behavioral changes. All existing tests pass.
The fix is verified both under pytest and in standalone Python invocation.
