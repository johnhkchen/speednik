# Design — T-011-04: camera-stability-tests

## Decision: Sim-level integration using `create_sim` + `camera_update`

### Approach chosen

Run `create_sim(stage)` to get a full `SimState`, then on each frame call `sim_step(sim, inp)`
followed by `camera_update(camera, sim.player, inp)`. Record camera position per frame.
After the run, apply stability assertions over the recorded trajectory.

This matches the ticket's prescribed pattern and mirrors how `main.py` works — simulation and
camera are updated sequentially each frame, camera is not part of SimState.

### Why not use `tests/harness.py`?

The harness uses `run_scenario` which calls `player_update` directly (not `sim_step`). It
skips entity interactions (springs, pipes, enemies). Springs launch the player violently,
which is exactly the kind of event that stresses camera tracking. Using `sim_step` captures
these interactions.

### Why not use `speednik/scenarios` runner?

The scenario runner in `speednik/scenarios/` returns `ScenarioOutcome` with `FrameRecord`
trajectory — but does not record camera state. We could extend it, but that would modify
production code for a test-only concern. Cleaner to build a thin camera-recording loop in
the test file.

### Strategies to test

**`hold_right`** — Baseline steady rightward movement. Tests horizontal tracking smoothness
on all terrain features. Uses harness-style strategy (simple `InputState(right=True)`).

**`spindash_right`** — High-speed player. Tests camera response to sudden acceleration and
deceleration. Stresses the horizontal scroll cap.

Both are available in `tests/harness.py`. Reuse those factory functions directly.

### Stages

All 3 stages: hillside, pipeworks, skybridge. The ticket's AC requires "all 3 stages."

### Frame count

Match walkthrough test budgets: hillside=4000, pipeworks=5000, skybridge=6000. These are
long enough to traverse meaningful portions of each stage.

## Stability assertions

### 1. Oscillation detection (no wobble)

**Algorithm**: Sliding window sign-flip counter.
- For each frame, compute `delta_x = cam_x[f] - cam_x[f-1]`.
- In a W-frame window, count how many times `sign(delta_x)` changes.
- Flag if flips > N (e.g., 5 flips in 10 frames).
- Exclude zero-delta frames (camera stationary in dead zone — not an oscillation).
- Do NOT exclude frames where player reverses — our strategies never reverse.

**Parameters**: W=10, N=5 (from ticket). Tunable if needed.

Apply to both X and Y axes.

### 2. No extreme jumps (delta bounds)

- `|delta_x| <= CAMERA_H_SCROLL_CAP + margin` every frame.
- `|delta_y| <= max(CAMERA_V_SCROLL_GROUND_FAST, CAMERA_V_SCROLL_AIR) + margin` every frame.
- Margin = 1.0 (floating-point tolerance).

### 3. Bounds clamping

- `camera.x >= 0` always.
- `camera.x + SCREEN_WIDTH <= sim.level_width` always (equivalently `camera.x <= level_width - SCREEN_WIDTH`).
- Same for Y: `camera.y >= 0` and `camera.y + SCREEN_HEIGHT <= sim.level_height`.

### 4. Player visibility

- `camera.x <= player.x <= camera.x + SCREEN_WIDTH` every frame.
- `camera.y <= player.y <= camera.y + SCREEN_HEIGHT` every frame.
- Exception: skip frames where `sim.player_dead` is True (player may be off-screen during
  death animation).

## Test organization

One test file: `tests/test_camera_stability.py`.

A helper function runs a full sim + camera trajectory for a (stage, strategy) combo and
returns the trajectory. Cache results across tests (same pattern as `test_walkthrough.py`).

Parametrize: 3 stages × 2 strategies = 6 combos.

Separate test methods for each assertion type so failures are specific and actionable.

## Rejected alternatives

**Extend ScenarioOutcome with camera fields**: Would require modifying `speednik/scenarios/runner.py`
and all downstream consumers. Not worth the coupling for a test-only need.

**Synthetic grid tests**: Could test camera on `build_flat()` grids, but the ticket explicitly
asks for "real stages" to catch terrain-induced camera stress (slopes, loops, springs).

**Per-axis separate test files**: Overkill. One file with clear test class separation is
sufficient.
