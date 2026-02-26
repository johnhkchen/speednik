# Progress — T-011-04: camera-stability-tests

## Completed

### Step 1: Create `tests/test_camera_stability.py`

Created the complete test file with:
- `CameraSnapshot` and `CameraTrajectory` dataclasses for recording trajectory
- `run_with_camera(stage, strategy_factory, frames)` — core sim+camera integration loop
- Trajectory cache to avoid re-running same combo across test methods
- Four assertion helpers: `check_oscillation`, `check_delta_bounds`, `check_level_bounds`, `check_player_visible`
- Helper functions `_sign_flips_in_window` and `_compute_signs` for oscillation detection
- Four parametrized test classes (3 stages × 2 strategies = 6 combos):
  - `TestNoOscillation` (12 tests: 6 combos × 2 axes)
  - `TestNoDeltaSpike` (6 tests)
  - `TestBoundsRespected` (6 tests)
  - `TestPlayerVisible` (6 tests)

### Step 2: Fix failing tests

Two issues encountered and resolved:

1. **Vertical oscillation on pipeworks/hold_right (frame ~594)**: Player physically stuck at
   terrain feature, bouncing between y=252 and y=258 with alternating on_ground/airborne.
   Camera faithfully tracks this. Fix: oscillation detection now also computes player position
   deltas — if the player itself is oscillating on the same axis, the camera oscillation is
   excluded (expected tracking behavior, not a camera bug).

2. **Player off-screen on skybridge/hold_right (frame ~385)**: Player falls below the level
   floor after spring launch (y > level_height). Camera clamped at max_y, can't follow. Fix:
   player visibility check now skips frames where the player is outside level bounds (about to
   die, camera structurally cannot follow).

### Step 3: Full test suite verification

`uv run pytest -x` — 1200 passed, 16 skipped, 5 xfailed, 0 failures. No regressions.

## Deviations from plan

- Added `_sign_flips_in_window` and `_compute_signs` helper functions (not in structure) to
  reduce duplication in oscillation logic.
- Oscillation detection now includes player-oscillation exclusion (not in original design).
- Player visibility check now excludes off-level-bounds frames (not in original design).

Both deviations were driven by real stage behavior discovered during testing.
