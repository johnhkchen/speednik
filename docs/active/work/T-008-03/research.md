# T-008-03 Research: Elemental Terrain Tests

## Goal

Write `tests/test_elementals.py` — micro-scenario tests on synthetic grids that
establish the mechanical boundaries of the physics engine. Five categories:
ground adhesion, walkability threshold, speed gates, loop traversal, gap clearing.

## Infrastructure (from T-008-01 and T-008-02)

### Harness (`tests/harness.py`)

- `run_scenario(tile_lookup, start_x, start_y, strategy, frames, on_ground)` →
  `ScenarioResult` with per-frame `FrameSnapshot` list.
- `ScenarioResult` properties: `final`, `max_x`, `quadrants_visited`, `stuck_at()`.
- Strategies: `idle()`, `hold_right()`, `hold_right_jump()`, `spindash_right()`,
  `scripted(timeline)`.
- `FrameSnapshot` fields: frame, x, y, x_vel, y_vel, ground_speed, angle,
  on_ground, quadrant, state.

### Grid Builders (`tests/grids.py`)

- `build_flat(width_tiles, ground_row)` — flat ground + fill.
- `build_slope(approach_tiles, slope_tiles, angle, ground_row)` — flat then
  constant-angle slope.
- `build_ramp(approach_tiles, ramp_tiles, start_angle, end_angle, ground_row)` —
  linearly interpolated angle ramp.
- `build_loop(approach_tiles, radius, ground_row, ramp_radius=None)` — full 360°
  loop with optional entry/exit ramps. Flat approach + flat exit.
- `build_gap(approach_tiles, gap_tiles, landing_tiles, ground_row)` — flat +
  gap + flat landing.
- All return `TileLookup` callables. No Pyxel imports.
- `FILL_DEPTH = 4` rows of solid below surface prevent sensor fall-through.

## Physics Engine Details

### Coordinate System

- Tile grid: `(tx, ty)` where `tx = px // 16`, `ty = py // 16`.
- Pixel (0,0) is top-left; Y increases downward.
- `ground_row=10` → ground surface at `y = 10 * 16 = 160` pixels.
- Player Y is center; standing player feet at `y + STANDING_HEIGHT_RADIUS`.
- For ground_row=10, player start_y should be `160 - STANDING_HEIGHT_RADIUS` but
  in practice `create_player` sets on_ground=True and collision snap handles it.
  Safest: place at `ground_row * 16` (surface top) and let floor snap adjust.

### Angles

- Byte angles: 0-255. Conversion: `byte = round(degrees * 256 / 360)`.
- 0 = flat, 64 = 90°, 128 = 180°, 192 = 270°.
- Common values: 20° ≈ byte 14, 30° ≈ byte 21, 45° ≈ byte 32, 60° ≈ byte 43,
  70° ≈ byte 50, 80° ≈ byte 57, 90° = byte 64.

### Quadrants (`get_quadrant(angle)`)

- Q0 (floor): angle 0–32 or 224–255.
- Q1 (right wall): 33–96.
- Q2 (ceiling): 97–160.
- Q3 (left wall): 161–223.

### Player Dimensions

- Standing: width_radius=9, height_radius=20.
- Rolling: width_radius=7, height_radius=14.
- Wall sensor extent: 10.

### Key Physics Constants

- `TOP_SPEED = 6.0` (walking max).
- `SPINDASH_BASE_SPEED = 8.0`.
- `GRAVITY = 0.21875`, `JUMP_FORCE = 6.5`.
- `SLOPE_FACTOR_RUNNING = 0.125` (gravity projection on slopes).
- `SLIP_ANGLE_THRESHOLD = 33` (~46° byte angle) — slopes steeper than this slip.
- `WALL_ANGLE_THRESHOLD = 48` (~67.5°) — wall sensor angle gate.

### Slope Mechanics

- Ground speed changes by `SLOPE_FACTOR * sin(angle)` each frame.
- At ~45° (byte 32), slope deceleration ≈ `0.125 * sin(π/4)` ≈ 0.088/frame.
  Walking accel is 0.046875/frame. Net negative → stalls.
- At ~30° (byte 21), slope decel ≈ 0.060/frame. Still net negative but barely.
- At ~20° (byte 14), slope decel ≈ 0.042/frame. Net positive → climbs.

### Loop Mechanics

- Loop tiles have `tile_type=SURFACE_LOOP`.
- Wall sensors exempt SURFACE_LOOP tiles (return `found=False`).
- Upper arc tiles have `solidity=TOP_ONLY`; lower arc `FULL`.
- Two-pass quadrant resolve ensures smooth quadrant transitions.
- Entry/exit ramps provide angle transitions (no ramps → abrupt wall hit).
- Speed needed: enough centripetal velocity to stay adhered through ceiling.

### Jump Physics

- Jump: initial `y_vel = -JUMP_FORCE = -6.5`, then `GRAVITY = 0.21875` each frame.
- Time to apex: `6.5 / 0.21875 ≈ 29.7 frames`.
- Peak height: `6.5² / (2 * 0.21875) ≈ 96.6 px`.
- Horizontal at TOP_SPEED: `6.0 * 59.4 ≈ 356 px` total flight distance.
- At spindash speed: `8.0 * 59.4 ≈ 475 px`.
- One tile = 16px. So ~22 tiles at walk speed, ~30 tiles at spindash.
  But air deceleration and trajectory curve reduce this significantly.

## Start Position Conventions

All grid builders place ground at `ground_row`. Surface y = `ground_row * 16`.
For approach tiles, the player should start on the flat section. With `ground_row=10`:
- Start x: `48.0` (3 tiles in, well on flat approach).
- Start y: `ground_row * 16 = 160` — collision snap adjusts to exact surface.

For the loop, with large `ground_row` (e.g., 40): start_y = `40 * 16 = 640`.

## Diagnostic Output

`ScenarioResult.stuck_at(tolerance, window)` returns the X where player stalled.
Assertion messages should include: stuck_at, final.x, final.y, final.angle,
final.on_ground, final.quadrant, final.ground_speed to enable diagnosis without
re-running.

## Test Patterns from Existing Tests

`test_harness.py` and `test_grids.py` use plain functions, `pytest.approx` for
float comparisons, no classes. Tests are short, one-assertion-per-concept.
`test_hillside_integration.py` uses `run_on_stage` for integration-level checks.

## Constraints

- No Pyxel imports.
- All grids from `tests/grids.py`.
- All strategies from `tests/harness.py`.
- `uv run pytest tests/test_elementals.py -x` must pass.
