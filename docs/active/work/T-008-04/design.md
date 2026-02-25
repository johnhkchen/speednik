# Design — T-008-04: Level Softlock Detection

## Core Decision: Physics-Only Simulation

### Option A: Extend harness with object processing (springs, pipes, etc.)
- Pro: Tests exactly match real gameplay
- Con: Significant harness change, out of scope for this ticket
- Con: Requires loading and processing entities each frame (springs, pipes, liquid)
- Con: Couples test code to game loop implementation details

### Option B: Physics-only with max_x comparison ← CHOSEN
- Pro: Uses existing harness as-is — no modifications to tests/harness.py
- Pro: max_x is a clean proxy for "did the player reach the goal area"
- Pro: Structural blockage detection works regardless of object interactions
- Con: Pipeworks/skybridge tests may be overly pessimistic (springs would help)
- Mitigation: If physics-only can't reach goal, that's useful info. Adjust frame
  counts or mark xfail with a reference to a future object-processing harness ticket.

**Rationale**: The ticket's code examples all use `result.max_x >= goal_x` which is
physics-only. The harness was deliberately designed this way. We should not change the
harness — just use it and let test results reveal what the levels actually require.

## Goal Position Extraction

### Option A: Parse entities.json directly in test file
- Con: Duplicates entity parsing logic

### Option B: Add `get_goal_x(stage_name)` helper to test file ← CHOSEN
- Uses `load_stage(stage_name).entities` to find goal entity
- Returns the X coordinate as a float
- Simple, self-contained, matches ticket's code example exactly

## Test Organization

### Per-stage test classes with shared stage cache

```
class TestHillside:
    test_hold_right_reaches_goal          # xfail until S-007
    test_spindash_reaches_goal
    test_no_structural_blockage

class TestPipeworks:
    test_hold_right_does_not_reach_goal   # design intent: gaps require jumping
    test_hold_right_jump_reaches_goal
    test_no_structural_blockage

class TestSkybridge:
    test_spindash_reaches_boss_area
    test_no_structural_blockage

class TestStallDetection:
    test_hillside_no_long_stall
```

### Strategy dictionary for structural blockage tests

```python
STRATEGIES = {
    "idle": idle,
    "hold_right": hold_right,
    "hold_right_jump": hold_right_jump,
    "spindash_right": spindash_right,
}
```

Each structural blockage test runs all strategies and asserts that at least one
reaches the goal. This catches level design defects (impassable terrain) vs.
intentional skill gates.

## Frame Counts

Following ticket guidance:
- Hillside: 3600 frames (60s) — generous for a 4800px stage
- Pipeworks: 3600 frames — same generosity for 5600px stage
- Skybridge: 5400 frames (90s) — extra time for spindash cycling on 5200px stage

## xfail Strategy

- `@pytest.mark.xfail(reason="S-007: loop blocks hold_right until ramp fix")`
- Applied only to `test_hold_right_reaches_goal` on hillside
- The spindash test should pass regardless (wall angle threshold exempts loop tiles)
- Structural blockage test should pass (spindash_right succeeds)

## Failure Messages

Every assertion includes the stall coordinate and strategy name:
```python
assert result.max_x >= goal_x, (
    f"hold_right stuck at x={result.stuck_at()}, goal at x={goal_x}"
)
```

## Key Design Decisions

1. **No harness modifications** — test file is self-contained
2. **Module-level stage cache** — avoid reloading stages per test (expensive JSON parsing)
3. **Separate `get_goal_x()` helper** — matches ticket spec, reusable across stages
4. **Class grouping by stage** — clear organization, easy to run one stage's tests
5. **Structural blockage as separate test** — the "meta" test that catches level defects
6. **Stall detection test for hillside only** — the "no stall >3 seconds" check as
   specified in the ticket, applied to the beginner level
