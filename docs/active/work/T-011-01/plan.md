# T-011-01 Plan: Stage Walkthrough Smoke Tests

## Step 1: Discover Actual Behavior

Before writing assertion thresholds, run all 9 (stage, strategy) combos and log the results.
This determines which combos reach the goal, where others get stuck, death counts, and ring
collection. Use a quick throwaway script via `uv run python -c "..."`.

**Verify**: Each combo produces a valid ScenarioOutcome with populated metrics.

## Step 2: Write `tests/test_walkthrough.py`

Create the test file with these sections in order:

### 2a: Imports and Constants
- Import `run_scenario`, `ScenarioDef`, `SuccessCondition`, `FailureCondition`
- Define `STAGES` dict: `{stage: {width, max_frames}}`
- Define `STRATEGIES` dict: `{strategy_name: {agent, agent_params}}`
- Define death caps and progress thresholds based on Step 1 findings

### 2b: Outcome Cache and Helpers
- Module-level `_OUTCOME_CACHE: dict[tuple[str,str], ScenarioOutcome] = {}`
- `_make_scenario(stage, strategy) → ScenarioDef`
- `_get_outcome(stage, strategy) → ScenarioOutcome` (caches)

### 2c: Test Class with Parameterized Methods
- `test_forward_progress` — all 9 combos: max_x > threshold
- `test_no_softlock` — all 9 combos: stuck_at is None (for combos that make forward progress)
- `test_rings_collected` — all 9 combos: rings > 0
- `test_spindash_reaches_goal` — spindash × 3 stages: success=True, reason=goal_reached
- `test_hillside_no_deaths` — 3 strategies × hillside: deaths == 0
- `test_deaths_within_cap` — all 9 combos: deaths ≤ cap
- `test_frame_budget` — goal-reaching combos: frames_elapsed ≤ 6000

### 2d: Documentation
- Add comments documenting which (stage, strategy) pairs reach goal vs get stuck
- Include observed max_x values for non-goal-reaching combos

## Step 3: Run Tests

Execute `uv run pytest tests/test_walkthrough.py -x -v` and verify all tests pass.

**Verify**:
- All 9 parameterized combos produce results
- spindash_right reaches goal on all 3 stages
- No unexpected test failures

## Step 4: Adjust Thresholds If Needed

If any tests fail due to incorrect thresholds (based on Step 1 data), adjust:
- Forward progress thresholds
- Death caps
- Max frames

Re-run tests until green.

## Step 5: Final Verification

Run the full test suite to confirm no regressions:
- `uv run pytest tests/test_walkthrough.py -x -v` (the new tests)
- `uv run pytest tests/ -x` (all tests — ensure no conflicts)

## Testing Strategy

- **Unit level**: Each test method asserts one specific property across parametrized combos
- **Integration level**: The test as a whole verifies end-to-end stage traversal
- **Verification criteria**: `uv run pytest tests/test_walkthrough.py -x` passes with 0 failures
- **No mocking**: All tests use real stage data and real simulation

## Commit Plan

Single atomic commit: "feat: add stage walkthrough smoke tests (T-011-01)"
- Creates `tests/test_walkthrough.py`
- No other file changes needed
