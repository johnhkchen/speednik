# T-011-01 Structure: Stage Walkthrough Smoke Tests

## Files

### Created
- `tests/test_walkthrough.py` — new file, ~200 lines

### Modified
- None

### Deleted
- None

## Module Boundaries

### `tests/test_walkthrough.py`

Single test file containing all walkthrough smoke tests. No new production code needed.

**Imports from speednik**:
- `speednik.scenarios.run_scenario` — drives simulation
- `speednik.scenarios.ScenarioDef` — scenario specification
- `speednik.scenarios.SuccessCondition` — success criteria
- `speednik.scenarios.FailureCondition` — failure criteria (compound `any`)
- `speednik.scenarios.ScenarioOutcome` — result type (for type clarity)

**Imports from stdlib/pytest**:
- `pytest` — parameterize, marks

## Internal Organization

### Constants Section
```
STAGES: dict mapping stage name → {width, max_frames}
STRATEGIES: dict mapping strategy name → {agent, agent_params}
DEATH_CAPS: dict mapping stage → max acceptable deaths
PROGRESS_THRESHOLDS: dict mapping stage → minimum max_x for forward progress
```

### Helper: `_make_scenario(stage, strategy, max_frames) → ScenarioDef`
- Constructs a ScenarioDef with:
  - success: `goal_reached`
  - failure: compound `any(player_dead, stuck(tolerance=2.0, window=120))`
  - metrics: `["max_x", "stuck_at", "rings_collected", "death_count", "completion_time"]`
- No YAML files needed — fully programmatic

### Helper: `_run(stage, strategy) → ScenarioOutcome`
- Calls `_make_scenario` then `run_scenario`
- Single entry point used by all test functions

### Test Class: `TestWalkthrough`

Parametrized across `(stage, strategy)` using the 9-combo matrix.

| Test Function | Assertion | All 9? |
|---------------|-----------|--------|
| `test_forward_progress` | max_x > 50% of width | Yes |
| `test_no_softlock` | stuck_at is None | Yes |
| `test_rings_collected` | rings_collected > 0 | Yes |
| `test_spindash_reaches_goal` | success=True, reason=goal_reached | spindash × 3 stages |
| `test_hillside_no_deaths` | deaths == 0 | 3 strategies × hillside |
| `test_deaths_within_cap` | deaths < cap | 9 combos |
| `test_frame_budget` | frames_elapsed ≤ 6000 | goal-reaching combos |

### Parametrize Strategy

Two parametrize decorators at class level:
1. `@pytest.mark.parametrize("stage", ["hillside", "pipeworks", "skybridge"])`
2. `@pytest.mark.parametrize("strategy", ["hold_right", "hold_right_jump", "spindash_right"])`

This gives `3 × 3 = 9` combinations for each test method.

### Fixture: `walkthrough_outcome`

A session-scoped or module-scoped fixture that caches `ScenarioOutcome` by `(stage, strategy)` key.
Running 6000 frames is fast (~0.1-0.3s) but running 9 × 6 tests = 54 invocations of the same
9 scenarios would be wasteful. Cache the 9 outcomes and let each test function read from the cache.

Implementation: module-level dict `_OUTCOME_CACHE: dict[tuple[str,str], ScenarioOutcome]`.
A helper function checks the cache before running.

### Selective Assertions

Some tests apply only to specific combos:
- `test_spindash_reaches_goal`: skip unless strategy is `spindash_right`
- `test_hillside_no_deaths`: skip unless stage is `hillside`
- `test_frame_budget`: skip unless outcome.success is True

Use `pytest.skip()` inside test body for conditional logic rather than complex
parametrize matrices.

## Interface with Scenario System

```
test_walkthrough.py
    │
    ├── ScenarioDef (constructed programmatically)
    │   ├── stage: str
    │   ├── agent: str (from STRATEGIES mapping)
    │   ├── agent_params: dict | None
    │   ├── max_frames: int (from STAGES mapping)
    │   ├── success: SuccessCondition(type="goal_reached")
    │   ├── failure: FailureCondition(type="any", conditions=[...])
    │   └── metrics: ["max_x", "stuck_at", "rings_collected", "death_count", ...]
    │
    └── run_scenario(sd) → ScenarioOutcome
        ├── .success: bool
        ├── .reason: str
        ├── .frames_elapsed: int
        └── .metrics: dict
```

No new public interfaces created. No changes to existing modules.
