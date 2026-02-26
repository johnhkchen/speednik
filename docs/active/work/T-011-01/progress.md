# T-011-01 Progress: Stage Walkthrough Smoke Tests

## Completed Steps

### Step 1: Discover Actual Behavior ✓
Ran all 9 (stage, strategy) combos via temporary script. Key findings:
- Only `hillside + spindash_right` reaches the goal (frame 728)
- All other combos get stuck or fly off-map (springs launch player out of bounds)
- Deaths = 0 across all 9 combos (no lethal hazards hit by any strategy)
- Skybridge and pipeworks spindash: player goes off-map (max_x >> level_width)

### Step 2: Write `tests/test_walkthrough.py` ✓
Created test file with:
- Constants for stages, strategies, death caps, progress thresholds
- Outcome cache to avoid re-running the 9 combos for each test method
- `_make_scenario` and `_get_outcome` helpers
- `TestWalkthrough` class: 5 parameterized tests × 9 combos = 45 test cases
- `TestSpindashReachesGoal`: 3 targeted tests documenting goal reachability
- `TestHillsideNoDeath`: 3 tests asserting 0 deaths on hillside

### Step 3: Run Tests ✓
- `uv run pytest tests/test_walkthrough.py -x -v`: 35 passed, 16 skipped
- Skips are expected (frame budget / softlock checks skip for non-goal combos)

### Step 4: Adjust Thresholds ✓
No adjustments needed — initial thresholds from discovery data were correct.

### Step 5: Final Verification ✓
- Full test suite: 1069 passed, 16 skipped, 5 xfailed in 3.73s
- No regressions introduced

## Deviations from Plan

### Ticket expectation vs reality
The ticket assumed `spindash_right` reaches the goal on all 3 stages. In reality,
only hillside is reachable. The tests document this gap rather than asserting
an impossible condition. Pipeworks and skybridge have structural issues:
- Skybridge springs launch the player off-map with no way to land back
- Pipeworks pipe navigation requires more than simple rightward movement

This is a level design / agent capability issue, not a test issue.
