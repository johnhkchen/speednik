# Research — T-012-06-BUG-03: slope-adhesion-fails-at-byte-angle-35

## Problem Statement

Player loses ground contact on slopes at byte angle >= 35 (~49°). The `on_ground`
ratio drops to ~50% in the slope region, well below the 80% threshold. The player
oscillates between on_ground and airborne while traversing steep slopes.

## Relevant Files

| File | Role |
|------|------|
| `speednik/grids.py` | `build_slope()` and `_slope_height_array()` — synthetic slope construction |
| `speednik/terrain.py` | Sensor casts, `find_floor()`, `resolve_collision()`, `get_quadrant()` |
| `speednik/physics.py` | `PhysicsState`, `apply_movement()`, slip system, `calculate_landing_speed()` |
| `speednik/constants.py` | `SLIP_ANGLE_THRESHOLD=33`, `SLIP_SPEED_THRESHOLD=2.5`, `SLIP_DURATION=30` |
| `tests/test_mechanic_probes.py` | `TestSlopeAdhesion` — parameterized test, xfail at angle>=35 |

## Height Array Generation (`_slope_height_array`)

`grids.py:45-67`. Computes 16-element height array for a tile:

```python
slope = -math.tan(rad)
h = 8.0 + (col_offset + col - 7.5) * slope
h_clamped = max(0, min(TILE_SIZE, round(h)))
```

At byte angle 35: `rad = 35 * 2π/256 ≈ 0.859`, `tan(0.859) ≈ 1.138`.
With `col_offset = i * 16`, each successive tile shifts the baseline by 16 * 1.138 ≈ 18.2
pixels per tile. After a few tiles, heights saturate at 0 or 16 for most columns,
producing binary (all-or-nothing) height arrays. This creates cliff-like tile profiles
instead of smooth slopes.

**Key observation:** At angle 35, tile i=2 has `col_offset=32`, so:
`h = 8.0 + (32 + col - 7.5) * (-1.138)`. For col=0: h = 8 + 24.5 * (-1.138) ≈ -19.9 → 0.
For col=15: h = 8 + 39.5 * (-1.138) ≈ -36.9 → 0.  The entire tile is empty (height=0).
But tile i=1 (col_offset=16) had columns that still produce non-zero heights. This means
consecutive slope tiles alternate between having surface and being empty, causing sensor
gaps.

## Quadrant Transition at Angle 35

`terrain.py:119-134`. `get_quadrant()` maps byte angles to quadrants:
- Quadrant 0 (normal): angle 0–32 or 224–255 → floor sensors point DOWN
- Quadrant 1 (right wall): angle 33–96 → floor sensors point RIGHT

At angle 35, the player enters quadrant 1. Floor sensors switch from casting
downward (using `_sensor_cast_down`) to casting rightward (using `_sensor_cast_right`).
This is a fundamental change in sensor behavior:

1. **Sensor placement changes** (`find_floor`, line 606-625): Quadrant 0 places A/B at
   feet spread by width_radius. Quadrant 1 places A/B to the right of the player center,
   spread vertically by width_radius.

2. **Cast direction changes**: Down-cast uses `height_array` directly. Right-cast uses
   `width_array()` logic (scanning columns for solid at a given row). These are completely
   different collision detection paths.

3. **Snap axis changes** (`_snap_to_floor`, line 982-992): Quadrant 0 snaps Y. Quadrant 1
   snaps X.

## The Oscillation Loop

When `build_slope` places all tiles at `ground_row` with angle=35:
1. Player starts on_ground, angle=35 → quadrant 1
2. Sensors cast RIGHT from the player → may or may not find surface (height arrays are
   nearly empty at steep col_offsets)
3. If no surface found within `_GROUND_SNAP_DISTANCE=14`, player detaches (on_ground=False)
4. Next frame: airborne, sensors cast DOWN (quadrant 0, angle=0)
5. Down-cast finds a tile below → player lands, angle set to tile's angle (35)
6. Back to step 1

This explains the ~50% on_ground ratio: the player alternates between ground (quadrant 1,
rightward sensors fail) and air (quadrant 0, downward sensors succeed, re-land).

## Slip System Interaction

`physics.py:338-352`. `check_slip` activates when:
- `on_ground` is true
- Angle >= 46° (byte angle >= 33)
- `ground_speed < 2.5`

At angle 35 (~49°), this is within the slip range. The slip timer is set to 30 frames.
During slip, `_apply_ground_input` ignores directional input and only applies friction,
which decelerates the player toward zero. This compounds the problem: as the player slows
down on the steep slope, the slip system activates, further reducing speed, and the reduced
ground_speed means less forward movement per frame — less chance to reach the next valid
surface tile before detaching.

## `build_slope` Architecture Issue

`grids.py:120-151`. All slope tiles are placed at `ground_row`. This means the surface is
supposed to be on a single horizontal row of tiles. But at steep angles, a real slope surface
would span multiple tile rows. The height arrays within a single tile row cannot represent
a surface that rises more than 16 pixels per 16 horizontal pixels — exactly a 45° limit.
Beyond that, the height arrays clip to 0 or 16, losing the actual surface shape.

This is the root geometric limitation. `build_slope` was designed for shallow slopes and
cannot represent slopes steeper than ~45° within a single tile row.

## Existing Test Coverage

`test_mechanic_probes.py:493-545`. `TestSlopeAdhesion` sweeps byte angles 0-45 in steps
of 5. Angles >= 35 are marked `xfail(strict=True)`. The test runs 300 frames of holding
right, then checks the on_ground ratio in the slope region (x=80 to x=320). The threshold
is 80%.

## Constraints and Boundaries

- `TILE_SIZE = 16`, `MAX_SENSOR_RANGE = 32`, `_GROUND_SNAP_DISTANCE = 14`
- Quadrant boundary at byte angle 33 is by-design (Sonic 2 spec)
- Slip system activation at ~46° is by-design
- `build_slope` is only used by test infrastructure, not by real stages
- Real stages (hillside, pipeworks, skybridge) have artist-authored tiles that naturally
  span multiple rows for steep sections

## Summary of Findings

Three interacting causes:

1. **Height array saturation**: `_slope_height_array` produces degenerate (all-0 or all-16)
   arrays when `col_offset` is large at steep angles. The slope surface disappears from tiles.

2. **Quadrant 1 sensor mismatch**: At angle 35, sensors cast rightward against tiles that
   have empty height arrays, failing to find surfaces.

3. **Single-row tile placement**: `build_slope` cannot represent steep slopes that naturally
   require multi-row tile layouts.

The slip system is a secondary amplifier, not a root cause.
