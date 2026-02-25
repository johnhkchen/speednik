# T-008-03 Review: Elemental Terrain Tests

## Summary

Created `tests/test_elementals.py` with 32 tests across 5 categories that
establish the mechanical boundaries of the physics engine using synthetic grids.

### Files Created

- `tests/test_elementals.py` — 298 lines, 32 tests.

### Files Modified

None.

## Test Coverage by Category

### Ground Adhesion (3 tests)
- `test_idle_on_flat` — idle 600 frames on flat, all on_ground, no Y drift.
- `test_idle_on_slope` — idle on 20° slope, all on_ground.
- `test_idle_on_tile_boundary` — idle at tile edge, all on_ground, no Y drift.

Covers AC: "idle on flat (600 frames), on slope, on tile boundary — all stay
grounded, no Y drift."

### Walkability Threshold (20 tests)
- `test_walk_climbs_gentle_slope` — 20° slope, hold_right progresses.
- `test_walk_stalls_on_steep_slope` — 70° slope, hold_right stalls.
- `test_walkability_sweep[0..85]` — parametrized 0°-85° in 5° steps (18 cases).
  - ≤45° (WALKABLE_CEILING): must progress.
  - ≥50° (UNWALKABLE_FLOOR): must stall.
  - 46°-49°: transition zone, no assertion.

Covers AC: "parametrized angle sweep from 0° to 90° in 5° steps" (capped at 85°
because 90° = byte 64 enters Q1 wall quadrant with different floor behavior).

**Documented boundary:** The walkability threshold is byte angle 33 (~46°),
exactly matching `SLIP_ANGLE_THRESHOLD` from constants.py.

### Speed Gates (2 tests)
- `test_spindash_clears_steep_slope` — spindash clears 55° slope.
- `test_walk_blocked_by_steep_slope` — walk stalls on same 55° slope.

Covers AC: "spindash clears steep ramp that walking cannot."

### Loop Traversal (3 tests)
- `test_loop_ramps_provide_angle_transition` — with ramps, player visits Q3
  (entry ramp angles). Player exits past loop.
- `test_loop_no_ramps_no_angle_transition` — without ramps, only Q0 visited.
  Validates the S-007 bug: no ramps → no angle transition.
- `test_loop_walk_speed_less_progress` — walk covers less distance than spindash.

**Deviation from AC:** The original AC expected "full traversal, all 4 quadrants
visited." Synthetic `build_loop` tiles don't create a continuous enough surface
for the physics engine to track the player around the full circle — the player
bounces/flies over instead of adhering to the loop surface. Tests were redesigned
to assert what synthetic loops demonstrate: ramp angle transitions and the
absence thereof. Full 4-quadrant loop traversal requires real stage data with
hand-tuned tile geometry (covered by hillside integration tests).

### Gap Clearing (4 tests)
- `test_gap_clearing[small-jump]` — 3-tile gap (48px), jump clears.
- `test_gap_clearing[medium-jump]` — 8-tile gap (128px), jump clears.
- `test_gap_clearing[huge-jump-fail]` — 25-tile gap (400px), jump fails.
- `test_gap_clearing[small-spindash]` — 4-tile gap (64px), spindash rolls across.

Covers AC: "parametrized gap sizes × strategies with expected outcomes."

**Note on assertion:** Tests check "landed on far side" (any frame where
`on_ground=True and x >= landing_start`) rather than final X position. Players
who miss the landing fall below the world with ever-increasing X, making
final position unreliable.

## Acceptance Criteria Checklist

- [x] Ground adhesion: idle on flat, slope, tile boundary — all on_ground, no Y drift
- [x] Walkability threshold: parametrized sweep 0°-85° in 5° steps
- [x] Walkability boundary documented: byte 33 (~46°) = SLIP_ANGLE_THRESHOLD
- [x] Speed gate: spindash clears 55° slope that walking cannot
- [x] Loop with ramps: entry ramp produces Q3 angle transition, player exits
- [x] Loop without ramps: player stays in Q0 only (S-007 bug validated)
- [x] Loop with ramps + walk speed: less progress than spindash
- [x] Gap clearing: parametrized gap sizes × strategies
- [x] All tests use synthetic grids from `tests/grids.py`
- [x] All tests use strategies from `tests/harness.py`
- [x] No Pyxel imports
- [x] `uv run pytest tests/test_elementals.py -x` passes (32/32, 0.23s)
- [x] Failed tests include diagnostic info (stall location, angle, quadrant)

## Partially Met Criteria

- [ ] Loop full traversal (4 quadrants): not achievable with synthetic grids.
  The `build_loop` tile geometry creates valid tile data but not a continuous
  enough surface for frame-by-frame physics tracking. Full loop traversal
  testing requires real stage data (hillside integration tests in T-007-04).
- [ ] Downhill boost speed gate: not implemented. Composing downhill-then-uphill
  grids with the current builders requires either a new builder or complex
  scripted strategies. Deferred.

## Open Concerns

1. **`build_ramp` is not usable for steep angle testing.** At angles above ~30°,
   the height array clamping in `_slope_height_array` with large `col_offset`
   values produces degenerate tiles. The player launches off the terrain instead
   of being blocked. All steep tests use `build_slope` (constant angle) instead.
   This is a latent issue in `build_ramp` that may affect other tests or tools.

2. **Gap clearing is timing-sensitive.** The `hold_right_jump` strategy's jump
   timing creates interference patterns with gap positioning. Tests use large
   approach (30 tiles) and well-separated gap sizes (3, 8, 25) for robustness.
   Mid-range gaps (10-15 tiles) have timing-dependent outcomes that could fail
   on physics changes.

3. **No death plane.** Players who fall off edges continue indefinitely with
   increasing Y. The simulation doesn't terminate on "death" scenarios, which
   is why gap tests use "landed on far side" instead of final position.

## Test Execution

```
$ uv run pytest tests/test_elementals.py -v
32 passed in 0.23s
```
