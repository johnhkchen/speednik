# T-013-01 Progress: World Boundary System

## Completed Steps

### Step 1: Add PIT_DEATH_MARGIN constant
- Added `PIT_DEATH_MARGIN = 32` to `speednik/constants.py:111`
- Positioned after `DEATH_DELAY_FRAMES` in the death-related constants section

### Step 2: Add kwargs to create_sim_from_lookup
- Updated `speednik/simulation.py:181-207` — added keyword-only `level_width` and
  `level_height` parameters with defaults of 99999
- This fixed TypeError in `tests/test_invariants.py` and `tests/test_qa_framework.py`
  where `make_sim()` passed these kwargs to `create_sim_from_lookup`

### Step 3: Add boundary enforcement to sim_step
- Added `PIT_DEATH_MARGIN` import to `speednik/simulation.py:10`
- Inserted boundary enforcement block in `sim_step()` after `player_update()` and before
  entity collision checks (~lines 226-249)
- Three boundaries enforced:
  - Left: clamp x to 0, zero negative x_vel/ground_speed
  - Right: clamp x to level_width, zero positive x_vel/ground_speed
  - Bottom: if y > level_height + 32, set state to DEAD, emit DeathEvent, increment deaths

### Step 4: Write tests
- Created `tests/test_world_boundary.py` with 11 tests across 3 test classes:
  - TestLeftBoundary (3 tests): clamp, velocity zero, no death
  - TestRightBoundary (2 tests): clamp, velocity zero
  - TestPitDeath (6 tests): triggers, event, counter, threshold, rings, idempotent

### Step 5: Run full test suite
- 11/11 new tests pass
- 22/22 invariant tests pass (previously 1 failing due to TypeError)
- 1021 total tests pass across suite
- 24 pre-existing failures (loop traversal, damage kills — unrelated)
- 34 xfail tests (expected)
- 5 test files excluded due to pre-existing ImportError (cast_terrain_ray)

## Deviations from Plan

- Pit death tests use `_make_pit_sim()` with empty tile lookup instead of `_make_sim()`.
  The original plan's `_make_sim()` creates ground tiles below level_height, so terrain
  collision catches the falling player before the pit death check triggers. Using an
  empty lookup ensures the player falls through to the pit boundary.

## Remaining

None. All planned steps complete.
