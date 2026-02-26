# T-013-05 Research: Loop and Slope Surface Adhesion

## Problem Statement

Three related failures: (1) loops never reach Q2 ceiling, (2) large loop exit
overshoot, (3) slope adhesion fails at byte angle ≥35.

## Current Physics Pipeline

`player_update` runs: `apply_input → apply_slope_factor → apply_gravity →
apply_movement → resolve_collision → update_slip_timer`.

### Ground-to-Air Transition (resolve_collision, terrain.py:766-850)

When `on_ground=True`, the engine runs `find_floor()`. If no floor found within
`_GROUND_SNAP_DISTANCE=14.0`, the player **detaches unconditionally**:

```python
if floor_result.found and abs(floor_result.distance) <= _GROUND_SNAP_DISTANCE:
    _snap_to_floor(state, floor_result, quadrant)
else:
    state.on_ground = False  # <-- unconditional detach
    state.angle = 0
```

**Critical finding**: There is NO speed-based adhesion check. The original Sonic 2
engine only detaches when `abs(ground_speed) < 2.5` AND angle is in the steep range
(46°-315°). The current engine detaches whenever the floor sensor can't find ground
within 14px, regardless of speed.

### Air-to-Ground Transition (resolve_collision, terrain.py:793-800)

Landing requires `y_vel >= 0` (falling downward) and floor within `_AIR_LAND_DISTANCE`.
This means a player moving upward on a right-wall surface (Q1, y_vel < 0) cannot re-land
even if they're right next to the surface.

### Slip System (physics.py:338-352)

```python
def check_slip(state):
    deg = _byte_angle_to_degrees(state.angle)
    on_steep_slope = 46.0 <= deg <= 315.0
    return abs(ground_speed) < SLIP_SPEED_THRESHOLD and on_steep_slope
```

When slip triggers: `slip_timer = 30`, input locked, only friction applies. This
causes ground_speed to decay → player detaches → lands → re-attaches → slips again.
The oscillation explains the ~50% on_ground ratio at steep angles.

### Sensor Quadrant Switching (terrain.py:100-115, 532-578)

`find_floor` uses `get_quadrant(state.angle)` to determine sensor direction:
- Q0 (angle 0-32, 224-255): sensors cast DOWN
- Q1 (angle 33-96): sensors cast RIGHT
- Q2 (angle 97-160): sensors cast UP
- Q3 (angle 161-223): sensors cast LEFT

The two-pass system (terrain.py:783-787) re-runs floor sensors when quadrant changes
after snapping. This is correct but insufficient — the player must first be on the
surface to get the new angle.

### Loop Tile Construction (grids.py:219-407)

`build_loop` traces a circle at sub-pixel resolution with traversal angles 0→255.
Tiles are `SURFACE_LOOP` type, `FULL` solidity. Height arrays are computed from
circle intersection with tile grid. The geometry is correct — angles are smooth
and progressive.

The SURFACE_LOOP exemption in `find_wall_push` (terrain.py:675-676) prevents wall
sensors from blocking loop traversal. This is working correctly.

## Root Cause Analysis

### Bug 1: Loop Q2 unreachable

The player enters the loop ramp, picks up Q1 angles (33-96). As the angle increases,
`apply_movement` decomposes ground_speed with increasing vertical component (moving up).
At the Q1→Q2 boundary (angle ~97), the floor sensor switches from RIGHT to UP.

**The problem**: On the frame where the quadrant transitions from Q1 to Q2, the player
is moving upward along the right wall. The UP-cast floor sensor must find the ceiling
surface. But the player has moved past the point where the 14px snap distance can reach
the ceiling tiles. The floor sensor returns `found=False`, and the engine detaches.

In the original Sonic 2, speed-based adhesion prevents this: if `ground_speed > 2.5`,
the player stays attached regardless of sensor gaps during quadrant transitions.

### Bug 2: Large loop overshoot

Secondary consequence of Bug 1. With radius ≥64, the player launches from a steeper
angle with more speed, creating a taller ballistic arc that overshoots exit tiles.

### Bug 3: Slope adhesion at angle ≥35

The slip system activates at 46° (byte angle ~33). On steep slopes, the sequence is:
1. Player on slope, ground_speed decays due to slope_factor
2. ground_speed drops below 2.5 → slip activates → input locked
3. Friction decays speed further → sensor loses contact → detach
4. Player falls, lands, re-attaches → loop repeats

The slip system itself is correct per Sonic 2 spec. The issue is that on detachment
(step 3), the engine doesn't check speed — it just detaches because the sensor gap
exceeds 14px. In Sonic 2, the player would stay attached as long as speed > 2.5.

## Relevant Sonic 2 Mechanics (from SPG)

1. **Fall condition**: Player detaches ONLY when `abs(ground_speed) < 2.5` AND angle
   is in 46°-315° range. At speeds ≥2.5, player stays attached to any surface.

2. **Control lock**: 30 frames of input lockout after slip (already implemented).

3. **Sensor snap range**: In Sonic 2, snap distance scales with speed:
   `min(abs(x_speed) + 4, 14)`. This is NOT implemented.

4. **Quadrant sensor switching**: Already implemented correctly.

## Files Involved

| File | Role | Lines |
|------|------|-------|
| `speednik/terrain.py` | `resolve_collision` — detachment logic | 766-850 |
| `speednik/physics.py` | `check_slip`, `update_slip_timer` | 338-352 |
| `speednik/constants.py` | `SLIP_ANGLE_THRESHOLD`, snap distances | 43-46 |
| `speednik/grids.py` | `build_loop` — loop tile construction | 219-407 |
| `tests/test_mechanic_probes.py` | Synthetic loop/slope tests | all |
| `tests/test_geometry_probes.py` | Hillside loop traversal tests | 195-274 |

## Key Constraint

The fix must not regress existing passing tests. Current pass: ramp entry, gap clearing,
spring launch, flat ground movement, hillside non-loop tests.
