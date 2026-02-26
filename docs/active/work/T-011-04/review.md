# Review — T-011-04: camera-stability-tests

## Summary

Added `tests/test_camera_stability.py` — integration tests that run the camera alongside
full simulation on real stages and assert stability properties. No production code modified.

## Files changed

| File | Action | Lines |
|---|---|---|
| `tests/test_camera_stability.py` | Created | ~310 |

## Test coverage

**30 parametrized test cases** across 3 stages × 2 strategies = 6 combos:

| Test class | Tests | What it checks |
|---|---|---|
| `TestNoOscillation` | 12 (6 × 2 axes) | No rapid sign-flips in camera deltas within sliding window |
| `TestNoDeltaSpike` | 6 | Per-frame camera delta ≤ scroll cap + 1px margin |
| `TestBoundsRespected` | 6 | Camera within [0, level_dim − screen_dim] always |
| `TestPlayerVisible` | 6 | Player within camera viewport (with documented exceptions) |

All 30 pass. Full suite: 1200 passed, 16 skipped, 5 xfailed.

## Acceptance criteria status

| AC | Status | Notes |
|---|---|---|
| Camera tracks hold_right on all 3 stages without oscillation | Pass | 6 oscillation tests pass |
| Camera tracks spindash_right without oscillation | Pass | 6 oscillation tests pass |
| No single-frame delta exceeds max scroll speed + margin | Pass | 6 delta-bounds tests pass |
| Camera never exceeds level bounds | Pass | 6 bounds tests pass |
| Player always visible on screen (with documented exceptions) | Pass | 6 visibility tests pass |
| Oscillation detection: sign-flip counting in sliding window | Pass | Implemented in `check_oscillation` |
| `uv run pytest tests/test_camera_stability.py -x` passes | Pass | 30/30 pass |

## Design decisions

1. **Sim-level integration**: Uses `create_sim` + `sim_step` + `camera_update` (not the
   harness's `run_scenario` which skips entity interactions like springs). This catches
   camera stress from spring launches and other entity-driven physics.

2. **Player-oscillation exclusion**: When the player itself physically oscillates (stuck at
   terrain feature), camera oscillation is expected tracking behavior. The oscillation
   detector compares camera sign-flips against player position sign-flips and excludes
   windows where both oscillate. This avoids false positives from legitimate physics.

3. **Off-level-bounds exclusion**: Player visibility skips frames where player is outside
   level bounds (falling off-map after spring launch). Camera is structurally clamped and
   cannot follow. This matches the ticket's "allow brief exceptions during death or pipe
   travel" guidance.

## Open concerns

1. **Pipeworks terrain stuck-bounce**: The player physically oscillates at a terrain feature
   around frame 594 (hold_right strategy). The camera correctly tracks this, but the
   underlying physics bounce may itself be a bug worth investigating separately. Not a camera
   issue.

2. **Skybridge off-map falls**: Springs on skybridge launch the player below the level floor
   (y > level_height) where they fall indefinitely. The camera handles this correctly (clamps
   at max_y), but the off-map escape is a known game issue per the walkthrough tests.

3. **Strategy coverage**: Only `hold_right` and `spindash_right` are tested. `hold_right_jump`
   could stress vertical tracking differently. Could be added in a follow-up if needed.

4. **Oscillation thresholds**: Window=10, max_flips=5 are from the ticket. These could be
   tightened or loosened based on gameplay experience. Current values pass all combos.
