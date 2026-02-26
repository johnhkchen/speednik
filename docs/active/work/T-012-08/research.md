# Research: T-012-08 — loop-traversal-audit

## Problem Statement

Existing loop tests accept "crossing the loop region aerially" as a pass. A proper
loop traversal means the player stays on the loop surface through all 4 quadrants
{0, 1, 2, 3} while on_ground. This ticket creates a QA audit test file that
asserts grounded traversal, parameterized across radii and entry speeds.

## Current Test Landscape

### `tests/test_mechanic_probes.py` — Existing synthetic loop probes

Uses `_run_mechanic_probe()` → `ProbeResult` with `FrameSnap` per frame.
`TestLoopEntry` class tests radii 32, 48, 64, 96 with spindash strategy.

Key difference from the audit: mechanic probes check `quadrants_visited` (any
frame, grounded or airborne). The audit must check `grounded_quadrants` only.

Current results with grounded check:
- r=32: grounded={0, 1} — fails (too small for tile sensors)
- r=48: grounded={0, 1, 2, 3} — passes
- r=64: grounded={0, 1, 2, 3} — passes (but never exits loop — BUG-02)
- r=96: grounded={0, 1, 2, 3} — passes (but never exits loop — BUG-02)

### `speednik/strategies.py` — Scenario runner

`run_scenario(tile_lookup, start_x, start_y, strategy, frames)` → `ScenarioResult`.
`FrameSnapshot` captures: x, y, x_vel, y_vel, ground_speed, angle, on_ground,
quadrant, state. Strategy type: `Callable[[int, Player], InputState]`.

Strategies: `spindash_right(charge_frames=3, redash_threshold=2.0)`, `hold_right()`,
`idle()`, `hold_right_jump()`, `scripted(timeline)`.

**Note**: The strategies module uses `player_update()` directly (not `sim_step()`).
No entities (rings, springs, etc.) affect the simulation. This is fine for synthetic
grid tests but means hillside tests need the `sim_step()` path to handle springs, etc.

### `tests/test_geometry_probes.py` — Real stage probes

Uses `_run_probe(stage, start_x, start_y, strategy, frames)` → `ProbeResult`.
Internally calls `create_sim(stage)` + `sim_step()`. The hillside loop probe
(TestLoopTraversal) starts at x=3100, y=610 and spindashes rightward.

Currently xfail'd for T-012-07 (angle smoothing). Only checks Q1 entry, not
full traversal. Has a `pytest` import bug (NameError) that prevents collection.

### `tests/test_audit_hillside.py` — Stage audit

Uses `speednik.qa` module's `run_audit()` with archetype-based strategies.
Different paradigm from what we need — audits are end-to-end stage walkthroughs,
not targeted loop probes.

## Simulation Infrastructure

### Two runner paths

1. **`run_scenario()` in `strategies.py`**: Uses `player_update()` directly.
   No entities. Takes `TileLookup`. Used by `test_elementals.py`.

2. **`sim_step()` in `simulation.py`**: Full game loop with entities. Takes
   `SimState`. Used by `test_mechanic_probes.py` and `test_geometry_probes.py`.

For the audit, synthetic tests can use either path. Hillside tests MUST use
`sim_step()` via `create_sim("hillside")` since the hillside loop geometry
comes from stage files.

### `create_sim(stage_name)` → `SimState`

Loads stage via `load_stage()`, creates player at `stage.player_start`, loads
all entities, returns `SimState`. For the audit, we override `player.physics.x`
and `player.physics.y` after creation to position near the loop.

### `create_sim_from_lookup(tile_lookup, start_x, start_y)` → `SimState`

Creates `SimState` from raw `TileLookup` with empty entity lists. Used for
synthetic grid tests.

## Loop Geometry

### `build_loop()` in `grids.py`

Signature: `build_loop(approach_tiles, radius, ground_row, ramp_radius=None)`
Returns: `(dict[tuple[int,int], Tile], TileLookup)`

Layout: flat approach → entry ramp (quarter circle) → loop circle (full 360°)
→ exit ramp (quarter circle) → flat exit.

Loop circle center: `cx = approach_px + ramp_radius + radius`,
`cy = ground_row * TILE_SIZE - radius`. All loop tiles: `solidity=FULL`,
`tile_type=SURFACE_LOOP`.

### Hillside loop coordinates

From geometry probe table: tiles tx=217–233, px 3472–3744, ground≈610.
Probe starts at x=3100, y=610 (well before the loop entry).

### Hillside loop behavior

Spindash from x=3100, y=610: player reaches Q1 (right-wall angles), then gets
stuck oscillating around x=3445–3449 in Q1. Ground speed decays from ~10 to
near zero. Player never reaches Q2 (ceiling). The hand-placed hillside tiles
have different geometry from `build_loop()` — likely steeper angle jumps that
trap the player.

## Quadrant System

`get_quadrant(angle)` maps byte angles:
- Q0: [0–32] ∪ [224–255] — floor, sensors DOWN
- Q1: [33–96] — right wall, sensors RIGHT
- Q2: [97–160] — ceiling, sensors UP
- Q3: [161–223] — left wall, sensors LEFT

## Speed Sensitivity

Tested r=48 with direct speed injection (no spindash):
- speed=5.0: full traversal ✓
- speed=8.0 (spindash base): full traversal ✓
- speed=4.0, 6.0, 7.0, 9.0, 10.0, 11.0, 12.0: all fail

Loop traversal is highly speed-sensitive — only narrow speed windows succeed.
This is consistent with the Sonic 2 engine where loop completion depends on
maintaining enough speed to overcome gravity through the ceiling section.

## File Structure for New Tests

Ticket specifies `tests/test_loop_audit.py` as the target file. No existing
file at that path.

## Dependencies

Ticket depends on T-012-01. The `speednik/grids.py` file (with the fixed
`build_loop()`) is already present in the workspace as an untracked file.
