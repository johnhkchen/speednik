# T-008-03 Design: Elemental Terrain Tests

## Decision: Test Structure

**Chosen approach:** Flat module with grouped test functions (no classes).

Matches the existing test pattern in `test_harness.py` and `test_grids.py`.
Test grouping via naming convention: `test_{category}_{specifics}`.

Rejected: pytest classes — adds boilerplate, no shared fixtures needed since each
test builds its own grid.

## Ground Adhesion Tests

Three tests that verify `idle()` on different terrain holds ground:

1. **`test_idle_on_flat`** — `build_flat(20, 10)`, idle 600 frames.
   Assert: all snapshots `on_ground=True`, final Y ≈ initial Y within 0.5px.

2. **`test_idle_on_slope`** — `build_slope(5, 10, angle_byte, 10)` with ~20° slope.
   Assert: all snapshots `on_ground=True`. Player may slide but never leaves ground.
   Note: sliding is expected behavior on slopes — we only assert ground contact.

3. **`test_idle_on_tile_boundary`** — `build_flat(20, 10)`, start_x exactly at
   tile boundary (e.g., `5 * 16 = 80.0`). Assert: all `on_ground`, Y stable.

## Walkability Threshold Tests

1. **`test_walk_climbs_gentle_slope`** — `build_ramp` with 20° end angle.
   `hold_right()` for 300 frames. Assert: X progresses, not stuck.

2. **`test_walk_stalls_on_steep_slope`** — `build_ramp` with 70° end angle.
   `hold_right()` for 300 frames. Assert: stuck (stuck_at returns a value).

3. **`test_walkability_sweep`** — Parametrized 0° to 90° in 5° steps.
   Build ramp to target angle, run `hold_right()`, measure progress.
   For each angle: if below threshold (≤30°) assert not stuck; if above (≥50°)
   assert stuck. The 35°–45° range is the transition zone — we document but use
   a looser assertion. The exact boundary depends on slope factor vs acceleration
   balance. We log the boundary angle for design reference.

   **Key insight from research:** slope deceleration = 0.125 * sin(angle).
   Walking acceleration = 0.046875. Equilibrium at sin(θ) = 0.375, θ ≈ 22°.
   But this is net ground_speed; momentum from approach means the player can push
   further. Empirically the boundary is likely 25°–35° range for sustained climb.
   We'll assert conservatively: ≤20° must progress, ≥50° must stall.

## Speed Gate Tests

1. **`test_spindash_clears_steep_ramp`** — Build ramp to ~50° (byte ~36).
   `spindash_right()` should clear it. Assert: X past ramp end, not stuck.

2. **`test_walk_blocked_by_steep_ramp`** — Same ramp geometry.
   `hold_right()` should stall. Assert: stuck_at returns a value, X < ramp end.

3. **`test_downhill_boost`** — Build a slope going down (angle in 192–255 byte
   range = descending right), then flat, then ascending ramp. Rolling downhill
   should build speed to clear the ascending ramp. Use `hold_right()` — gravity
   boost from downhill should suffice.

   Actually, simpler: `build_ramp` from angle 0 to ~240 (downhill) approach,
   then another ramp uphill. This is complex to compose.

   **Revised:** Use `scripted()` strategy — hold right on a downhill slope
   to build speed, then hit an uphill ramp. Or just test that spindash clears
   a ramp that walking cannot — that's the core speed gate assertion. Downhill
   boost is secondary; skip if too complex for the grid composition.

## Loop Traversal Tests

1. **`test_loop_spindash_traversal`** — `build_loop(10, 128, 40, ramp_radius=128)`.
   `spindash_right()` for 600 frames. Assert: `quadrants_visited >= {0,1,2,3}`,
   final X past the loop exit.

2. **`test_loop_no_ramps_blocked`** — `build_loop(10, 128, 40, ramp_radius=None)`.
   `spindash_right()` for 600 frames. Assert: player doesn't traverse, stuck at
   loop entry area. Final X < loop midpoint.

3. **`test_loop_walk_speed_fails`** — `build_loop(10, 128, 40, ramp_radius=128)`.
   `hold_right()` for 600 frames. Assert: insufficient speed to complete loop.
   Final X < loop exit.

**Loop geometry for assertions:** With approach_tiles=10 and radius=128:
- approach_px = 160. ramp_entry starts at 160. loop_start = 288.
- loop_end = 544. ramp_exit_end = 672.
- loop_exit_x ~ 672 px. Loop midpoint ~ 416 px.

## Gap Clearing Tests

Parametrized: `(gap_tiles, strategy_factory, should_clear)`.

- (2, hold_right_jump, True) — 32px gap, trivially jumpable.
- (6, hold_right_jump, True) — 96px gap, medium.
- (12, hold_right_jump, False) — 192px gap, too far for walking jump.
- (8, spindash_right, True) — 128px gap, spindash speed clears without jump.

Assert based on `should_clear`:
- If True: final X past gap landing start.
- If False: final X in the gap or before it (fell).

**Gap geometry:** `build_gap(approach, gap, landing, ground_row)`.
Approach = 10 tiles. Gap start = 10*16 = 160px. Landing start = (10+gap)*16.

## Assertion Messages

Every assertion includes a diagnostic f-string:
```python
assert condition, (
    f"<description> | x={r.final.x:.1f} y={r.final.y:.1f} "
    f"gspd={r.final.ground_speed:.2f} angle={r.final.angle} "
    f"on_ground={r.final.on_ground} stuck={r.stuck_at()}"
)
```

## Conventions

- `ground_row = 10` for most tests (surface at y=160).
- `ground_row = 40` for loop tests (surface at y=640, need room above for loop).
- `start_x = 48.0` (3 tiles in on flat approach).
- `start_y = ground_row * TILE_SIZE` (surface; collision snap adjusts).
- Import `TILE_SIZE` from `speednik.terrain` for computing positions.
- Helper: `_deg_to_byte(deg)` for angle conversion.
