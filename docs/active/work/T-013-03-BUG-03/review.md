# Review — T-013-03-BUG-03: Speed Demon Pit Death on Skybridge

## Summary

Fixed a collision data bug in the Skybridge stage that caused the speed demon archetype
to hit an invisible wall at bridge-to-slope transition points, lose all horizontal
momentum, and fall to pit death. The fix involved three coordinated changes to the stage
collision and tile data files.

## Files Changed

### `speednik/stages/skybridge/collision.json` (modified)
- **278 cells** changed from FULL(2) → TOP_ONLY(1) across four regions:
  - Transition 1 (cols 48-55, rows 30-39): downslope after bridge segment 4
  - Transition 2 (cols 100-107 + 118-122, rows 30-39): slope pillar between segments 5-6
  - Transition 3 (cols 150-157 + 168-172, rows 30-39): slope pillar between segments 6-7
  - Boss arena entrance (cols 250-259, rows 28-39): transition to final arena
- **36 cells** added as TOP_ONLY(1) in bridge gaps:
  - Cols 73-76, rows 31-32: gap between slope exit and bridge 5
  - Cols 123-128, rows 31-32: gap between slope exit and bridge 6
  - Cols 173-180, rows 31-32: gap between slope exit and bridge 7

### `speednik/stages/skybridge/tile_map.json` (modified)
- **27 wall tiles** neutralized: tiles with angle=64 (left-wall orientation) had their
  height_array set to [0]*16 and angle set to 0, preventing wall-climbing behavior
  when accessed with TOP_ONLY solidity
- **36 bridge tiles** added: standard flat bridge tiles in the gap regions listed above,
  providing landing surface for airborne players exiting slopes

### Files NOT changed
- No physics code, simulation code, or test code modified
- `entities.json` — no changes (recovery spring was tried and reverted)
- No changes to other stages (hillside, pipeworks)

## Root Cause

The collision.json solidity values for the slope/pillar structures between bridge segments
were set to FULL (2), while the tile_map.json declared the same tiles as type=1 (TOP_ONLY).
This mismatch meant:

1. Wall sensors detected the pillar tiles as solid walls, blocking horizontal movement
2. A fast-moving airborne player hitting the pillar wall had x_vel zeroed
3. With zero horizontal velocity over a bridge gap, the player fell to pit death
4. Respawn at checkpoint sent the player back into the same trajectory → infinite death loop

The tile_map type=1 declaration was correct (skybridge pillars should only collide from
above, allowing passage from the sides), but the collision.json type=2 overrode this.

## Test Coverage

### Direct verification
- Speed demon audit: max_x=5136, deaths=0, goal_reached=True (was: max_x=1590, deaths=6)
- All 6 archetypes tested on Skybridge: no new deaths at fixed transitions
- `test_skybridge_speed_demon`: now XPASS (passes when the test expected failure)

### Regression checks
- Hillside integration tests: 10 passed, 5 xfailed, 1 pre-existing failure
- Hillside audit tests: no change
- Full test suite (excluding pre-existing import errors): 1028 passed, 32 failed
  - All 32 failures are pre-existing (loop tests, pipeworks tests, boundary tests)
  - No new failures introduced

## Open Concerns

1. **test_skybridge_speed_demon XPASS**: The test now passes but still has an xfail marker
   referencing T-013-03-BUG-03. The parent ticket T-013-03 should remove the xfail marker.

2. **Ticket description accuracy**: The ticket describes death at x≈690, but the actual
   death (on current HEAD) occurs at x≈1590. Earlier collision fixes (T-013-01/T-013-02)
   likely resolved the original x≈690 failure. The fix addresses the actual failure point.

3. **Broad solidity change scope**: The fix changes 314 collision cells. While all changes
   align tile_map intent with collision reality, the broad scope means visual testing of
   all transition points would be valuable to confirm no unintended gameplay changes
   (e.g., enemies falling through pillars, rings becoming unreachable).

4. **Other archetypes**: Walker and wall_hugger max_x is only ~228 (they walk off the first
   bridge gap). Jumper reaches x=2169. These are pre-existing limitations of those
   archetypes on this stage, not regressions.

5. **Pre-existing test failures**: 32 tests fail in the full suite, primarily loop traversal
   tests and pipeworks audit tests. These are tracked by other tickets (T-013-05 for loop
   adhesion) and are unrelated to this fix.
