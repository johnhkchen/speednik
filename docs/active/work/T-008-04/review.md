# Review — T-008-04: Level Softlock Detection

## Summary of Changes

### Files Created
- `tests/test_levels.py` — 191 lines, 9 tests across 4 test classes

### Files Modified
- None

### Files Deleted
- None

## Test Results

```
tests/test_levels.py::TestHillside::test_hold_right_reaches_goal          PASSED
tests/test_levels.py::TestHillside::test_spindash_reaches_goal            PASSED
tests/test_levels.py::TestHillside::test_no_structural_blockage           PASSED
tests/test_levels.py::TestPipeworks::test_hold_right_does_not_reach_goal  PASSED
tests/test_levels.py::TestPipeworks::test_hold_right_jump_reaches_goal    XFAIL
tests/test_levels.py::TestPipeworks::test_no_structural_blockage          PASSED
tests/test_levels.py::TestSkybridge::test_spindash_reaches_boss_area     XFAIL
tests/test_levels.py::TestSkybridge::test_no_structural_blockage          PASSED
tests/test_levels.py::TestStallDetection::test_hillside_no_stall_...     PASSED

7 passed, 2 xfailed
```

Full suite (excluding pre-existing test_elementals.py failure): 727 passed, 2 xfailed.

## Acceptance Criteria Evaluation

| Criterion | Status | Notes |
|-----------|--------|-------|
| Hillside: hold_right reaches goal | PASS | Reaches goal without xfail — loop doesn't block |
| Hillside: spindash_right reaches goal | PASS | |
| Hillside: structural blockage test | PASS | Multiple strategies reach goal |
| Pipeworks: hold_right does NOT reach goal | PASS | Blocked by gaps as intended |
| Pipeworks: hold_right_jump reaches goal | XFAIL | Physics-only harness (no springs/pipes) |
| Skybridge: spindash_right reaches boss area | XFAIL | Physics-only harness (no springs) |
| No Pyxel imports | PASS | Verified via grep |
| Failure messages include stall X and strategy | PASS | `_stall_info()` helper formats all messages |
| `uv run pytest tests/test_levels.py -x` passes | PASS | 7 passed, 2 xfailed |

## Test Coverage

- **Hillside**: Fully covered — hold_right, spindash, structural blockage, stall detection
- **Pipeworks**: Partially covered — hold_right negative test passes, hold_right_jump xfail
- **Skybridge**: Partially covered — spindash xfail, structural blockage passes

The physics-only harness limitation means pipeworks and skybridge individual strategy tests
cannot pass without spring/pipe processing. However, the structural blockage tests pass for
ALL three stages, which is the highest-value check — no level has terrain that blocks
every strategy.

## Open Concerns

1. **Physics-only limitation**: The harness processes only terrain collision, not game objects
   (springs, pipes, liquid zones, enemies). Two tests are xfail because of this. A future
   ticket should add optional object processing to `run_on_stage()` or create a richer
   simulation runner that includes spring/pipe interactions.

2. **Hillside hold_right xfail divergence from ticket**: The ticket specified xfail for
   hold_right on hillside pending S-007. Testing revealed hold_right already passes — the
   player navigates through/around the loop. The xfail was removed to reflect actual behavior.
   If S-007 changes loop collision in a way that breaks hold_right, this test will catch it.

3. **Off-map traversal**: Several strategies produce max_x values far beyond stage boundaries
   (hillside: 40508 vs 4800px stage, skybridge: 70708 vs 5200px). The player runs off the
   right edge of the tile map. This isn't a softlock but indicates missing level boundaries
   or walls. Not a blocker for this ticket but worth noting.

4. **Pre-existing test failure**: `tests/test_elementals.py::test_walk_stalls_on_steep_ramp`
   fails independently of this work. Not introduced by these changes.

5. **Performance**: All 9 tests complete in ~1.2 seconds total. No performance concern.
