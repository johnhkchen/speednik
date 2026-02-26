# Plan — T-011-04: camera-stability-tests

## Step 1: Create `tests/test_camera_stability.py` with infrastructure

Write the complete file in one pass:

1. Imports from `speednik.camera`, `speednik.simulation`, `speednik.constants`, `speednik.physics`,
   `tests.harness`.
2. `CameraSnapshot` and `CameraTrajectory` dataclasses.
3. `run_with_camera(stage, strategy_factory, frames)` — the core sim+camera loop.
4. Trajectory cache (`_TRAJECTORY_CACHE`, `get_trajectory`).
5. Stage/strategy constants and assertion parameters.
6. Four assertion helper functions:
   - `check_oscillation(trajectory, axis)` — sliding window sign-flip counter.
   - `check_delta_bounds(trajectory)` — per-frame delta vs scroll cap.
   - `check_level_bounds(trajectory)` — camera within [0, max].
   - `check_player_visible(trajectory)` — player within camera viewport.
7. Four test classes with parametrized tests:
   - `TestNoOscillation` — horizontal and vertical oscillation.
   - `TestNoDeltaSpike` — no extreme camera jumps.
   - `TestBoundsRespected` — camera within level bounds.
   - `TestPlayerVisible` — player always on screen.

**Verification**: `uv run pytest tests/test_camera_stability.py -x -v`

## Step 2: Fix any failing tests

If any combo fails (likely pipeworks/skybridge with springs launching player off-map):

- Adjust player-visibility to skip dead frames (already planned via `player_dead` flag).
- If player goes truly off-level-bounds (below floor), document as known behavior and
  add appropriate skip conditions if needed.
- Tune oscillation parameters if legitimate terrain features (e.g., slope transitions)
  cause brief sign flips.

**Verification**: `uv run pytest tests/test_camera_stability.py -x -v` — all green.

## Step 3: Verify full test suite

Run the complete test suite to make sure nothing else broke.

**Verification**: `uv run pytest -x`

## Testing strategy

- **Primary**: `uv run pytest tests/test_camera_stability.py -x -v` — the new test file.
- **Regression**: `uv run pytest -x` — full suite.
- **No mocks**: Real stages, real simulation, real camera. Integration tests by design.
- **Coverage**: 6 combos (3 stages × 2 strategies) × 4 assertion types = 24 test cases
  (parametrized), plus 2 oscillation axes = ~30 individual assertions.

## Acceptance criteria mapping

| AC | Test |
|---|---|
| Camera tracks hold_right on all 3 stages without oscillation | `TestNoOscillation` × 3 stages × hold_right |
| Camera tracks spindash_right without oscillation | `TestNoOscillation` × 3 stages × spindash_right |
| No single-frame delta exceeds max scroll speed + margin | `TestNoDeltaSpike` × 6 combos |
| Camera never exceeds level bounds | `TestBoundsRespected` × 6 combos |
| Player always visible on screen | `TestPlayerVisible` × 6 combos |
| Oscillation detection: sign-flip counting in sliding window | `check_oscillation` implementation |
| `uv run pytest tests/test_camera_stability.py -x` passes | Step 2 verification |
