# Plan — T-008-04: Level Softlock Detection

## Step 1: Create tests/test_levels.py with helpers

Write the complete test file with:
- Imports (pytest, load_stage, harness strategies)
- Module-level stage cache (`_cached_stages` dict, `_get_stage()` function)
- `get_goal_x(stage_name)` helper
- `STRATEGIES` dictionary

Verify: File parses without syntax errors.

## Step 2: Implement TestHillside class

Three tests:
1. `test_hold_right_reaches_goal` — `@pytest.mark.xfail(reason="S-007: ...")`,
   run hold_right for 3600 frames, assert max_x >= goal_x
2. `test_spindash_reaches_goal` — run spindash_right for 3600 frames,
   assert max_x >= goal_x
3. `test_no_structural_blockage` — run all STRATEGIES, assert best max_x >= goal_x

All assertions include stall coordinate in message.

Verify: `uv run pytest tests/test_levels.py::TestHillside -x`

## Step 3: Implement TestPipeworks class

Three tests:
1. `test_hold_right_does_not_reach_goal` — assert max_x < goal_x (gaps require jumping)
2. `test_hold_right_jump_reaches_goal` — assert max_x >= goal_x
3. `test_no_structural_blockage` — run all STRATEGIES, assert best max_x >= goal_x

Verify: `uv run pytest tests/test_levels.py::TestPipeworks -x`

## Step 4: Implement TestSkybridge class

Two tests:
1. `test_spindash_reaches_boss_area` — run spindash_right for 5400 frames,
   assert max_x >= boss threshold (use goal_x or a defined boss area X)
2. `test_no_structural_blockage` — run all STRATEGIES for 5400 frames

Verify: `uv run pytest tests/test_levels.py::TestSkybridge -x`

## Step 5: Implement TestStallDetection class

One test:
1. `test_hillside_no_stall_longer_than_3_seconds` — run hold_right_jump for 3600 frames,
   scan snapshots for any X where player stays within tolerance=2.0 for 180+ frames

Verify: `uv run pytest tests/test_levels.py::TestStallDetection -x`

## Step 6: Full test suite validation

Run: `uv run pytest tests/test_levels.py -v`
- Expect: all tests pass (with hillside hold_right as xfail)
- Check: no Pyxel imports in the file
- Check: assertion messages include stall coordinates

If any tests unexpectedly fail (e.g., pipeworks hold_right_jump doesn't reach goal
because springs aren't processed), mark as xfail with a clear reason referencing
the physics-only limitation, and document in progress.md.

## Step 7: Run full test suite

Run: `uv run pytest tests/ -x`
- Verify no regressions in existing tests
- Verify test_levels.py integrates cleanly

## Testing Strategy

- **Unit tests**: Not applicable — this IS the test file
- **Integration tests**: Each test IS an integration test (real stage data + physics engine)
- **Verification**: Pass/fail of the test suite itself is the verification
- **xfail**: Used for known-incomplete features (S-007), not for broken tests

## Risk: Long-running tests

3600-frame simulations with real stage data may be slow (~seconds per test).
Acceptable for CI. If too slow, can add `@pytest.mark.slow` marker for selective runs.
