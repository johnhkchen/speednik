# T-011-03 Review: Geometric Feature Probes

## Summary of Changes

### Files Created
- `tests/test_geometry_probes.py` — 12 tests across 5 test classes

### Files Modified
- None

## Test Coverage

| Feature    | Class                    | Tests | Stage     | Assertions                                   |
|------------|--------------------------|-------|-----------|----------------------------------------------|
| Loop       | TestLoopTraversal        | 4     | hillside  | Quadrant 1 entry, cross region, speed, ground|
| Spring     | TestSpringLaunch         | 3     | hillside  | Event fires, height gain, landing            |
| Gap        | TestGapClearing          | 2     | skybridge | Crosses gap, stays above death threshold     |
| Ramp       | TestRampTransition       | 2     | hillside  | No velocity zeroing, smooth angle changes    |
| Checkpoint | TestCheckpointActivation | 1     | hillside  | CheckpointEvent fires                        |

All 12 tests pass. Suite runs in ~0.12s.

## Acceptance Criteria Status

- [x] Loop probe: spindash through hillside loop, quadrant 1 (right-wall) visited
- [x] Loop probe: player exits with positive speed and returns to ground level
- [x] Spring probe: spring launch detected, player gains expected height
- [x] Gap probe: player clears gap per stage with hold_right_jump
- [x] Ramp probe: no velocity zeroing on slope transitions
- [x] Checkpoint probe: CheckpointEvent fires when player reaches checkpoint
- [x] Probe coordinates documented in comments for maintainability
- [x] `uv run pytest tests/test_geometry_probes.py -x` passes

### Partial: Loop all-4-quadrants

The original AC specifies "all 4 quadrants visited" for the loop probe. Investigation
revealed the current physics engine does not support full loop traversal — the player
launches over the loop ramp at spindash speed rather than running through all 4 quadrants.
The walkthrough test (T-011-01) confirms this: even the successful hillside spindash run
arcs over the loop airborne, only touching quadrant 1 briefly before going ballistic.

The loop tests verify the achievable behavior: entry into quadrant 1 (right-wall angle),
crossing the full loop region, exiting with positive speed, and returning to ground.

## Architecture

The test file is self-contained — no dependency on `tests/harness.py` or
`speednik/scenarios/`. Uses `create_sim()` + `sim_step()` directly via a thin
`_run_probe()` helper. Strategy factories create closures with isolated state
(no shared globals between tests).

## Open Concerns

1. **Loop traversal limitation**: The engine doesn't support full 360-degree loop
   running. If loop physics are improved in the future, the loop tests should be
   updated to assert all 4 quadrants.

2. **Coordinate fragility**: All probe coordinates are hard-coded from current stage
   data. If stages are regenerated (`svg2stage` or `profile2stage` rerun), coordinates
   may shift. Each test class documents its coordinates in the docstring and inline
   comments for easy updating.

3. **Single stage per feature**: Most probes target hillside (the simplest stage).
   Gap clearing uses skybridge. Pipeworks has no dedicated probes. This could be
   expanded in a future ticket.

4. **Spring landing coverage**: The spring landing test checks that the player
   returns to `on_ground` within 120 frames, but doesn't verify the landing position
   matches expected terrain. This is sufficient for a geometry regression test but
   could be more precise.
