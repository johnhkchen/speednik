# Structure — T-008-04: Level Softlock Detection

## Files

### Created: `tests/test_levels.py`

Single new test file. No modifications to any existing file.

## Module Layout

```
tests/test_levels.py
├── Imports
│   ├── pytest
│   ├── speednik.level.load_stage
│   └── tests.harness.{run_on_stage, idle, hold_right, hold_right_jump, spindash_right}
│
├── Helpers
│   ├── _cached_stages: dict[str, StageData]     # module-level cache
│   ├── _get_stage(name) -> StageData             # lazy-load with cache
│   ├── get_goal_x(stage_name) -> float           # extract goal X from entities
│   └── STRATEGIES: dict[str, Strategy]           # named strategy dictionary
│
├── class TestHillside
│   ├── test_hold_right_reaches_goal()            # xfail(S-007)
│   ├── test_spindash_reaches_goal()
│   └── test_no_structural_blockage()
│
├── class TestPipeworks
│   ├── test_hold_right_does_not_reach_goal()
│   ├── test_hold_right_jump_reaches_goal()
│   └── test_no_structural_blockage()
│
├── class TestSkybridge
│   ├── test_spindash_reaches_boss_area()
│   └── test_no_structural_blockage()
│
└── class TestStallDetection
    └── test_hillside_no_stall_longer_than_3_seconds()
```

## Interface Contracts

### `get_goal_x(stage_name: str) -> float`
- Loads stage, filters entities for `type == "goal"`, returns first match's X
- Raises AssertionError if no goal found (fail-fast in tests)

### `STRATEGIES` dict
```python
STRATEGIES: dict[str, Callable] = {
    "idle": idle,
    "hold_right": hold_right,
    "hold_right_jump": hold_right_jump,
    "spindash_right": spindash_right,
}
```
- Keyed by human-readable name for assertion messages
- Values are factory functions (call to get strategy callable)

### `_get_stage(name: str) -> StageData`
- Module-level cache dict `_cached_stages`
- Loads once per stage name, returns cached thereafter
- Avoids repeated JSON parsing across tests in the same class

## Dependencies

### Imports from project
- `speednik.level.load_stage` — stage loading
- No `speednik.objects` imports (physics-only testing)
- No Pyxel imports

### Imports from test infrastructure
- `tests.harness.run_on_stage` — simulation runner
- `tests.harness.{idle, hold_right, hold_right_jump, spindash_right}` — strategies

### External
- `pytest` — test framework, xfail marker

## Boundaries

- This file does NOT modify the harness
- This file does NOT process game objects (springs, pipes, enemies)
- This file does NOT import Pyxel
- All assertions include descriptive messages with coordinates and strategy names
- Frame counts: 3600 (hillside, pipeworks), 5400 (skybridge)
