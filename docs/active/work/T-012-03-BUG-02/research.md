# Research: T-012-03-BUG-02 — Pipeworks Solid Tile Clipping

## Bug Characterization

The ticket describes 150 `inside_solid_tile` invariant errors for Walker/Wall Hugger
at x=3042-3094. Actual reproduction shows **1438 errors** spanning x=3444 to x=3698,
starting at frame 639. The player enters the solid interior of pipe structures while
airborne at high speed, then oscillates between solid tiles indefinitely.

## Relevant Source Files

| File | Role |
|------|------|
| `speednik/terrain.py` | Tile collision: sensors, solidity, `resolve_collision()` |
| `speednik/physics.py` | Movement engine: `apply_movement()` adds vel to pos in one step |
| `speednik/player.py` | `player_update()`: physics steps 1-4, then collision steps 5-7 |
| `speednik/simulation.py` | `sim_step()`: calls `player_update()`, boundary clamps |
| `speednik/invariants.py` | `_check_inside_solid()`: flags player center inside FULL tiles |
| `speednik/level.py` | Loads tile_map.json + collision.json into `Tile` dict |
| `speednik/stages/pipeworks/tile_map.json` | Tile height arrays and angles |
| `speednik/stages/pipeworks/collision.json` | Solidity flags per tile position |

## Tile Layout: Pipe Structures

Pipeworks has two main pipe structures in the clipping zone:

**Pipe A** (x=3440-3584, y=400-480): cols 215-224, rows 25-30
- Left wall: (215,25) and (215,26), angle=64, sol=FULL, ha has zeros in cols 0-9
- Cap: (216-224,25), angle=0, sol=FULL, ha=[16]*16
- Ceiling: (216-224,26), angle=128, sol=FULL, ha=[16]*16
- Solid fill: (215-224,27-30), angle=0, sol=FULL, ha=[16]*16

**Pipe B** (x=3600-3744, y=288-480): cols 225-234, rows 18-30
- Left wall: (225,18-19), angle=64, sol=FULL
- Cap: (226-234,18), angle=0, sol=FULL, ha=[4]*16
- Ceiling: (226-234,19), angle=128, sol=FULL, ha=[4]*16
- Right wall: (225,25), angle=192 (left wall from other side)
- Solid fill: (225-234,20-30), angle=0, sol=FULL, ha=[16]*16

There is a 2-column gap (cols 213-214) before Pipe A, and a gap before col 215 in
rows 24-26. The pipes are entirely filled with FULL solidity tiles.

## Frame Update Order

In `player_update()` (player.py:109):
1. `_pre_physics()` — state transitions (jump, roll, spindash)
2. `apply_input()` — acceleration/deceleration
3. `apply_slope_factor()` — gravity on slopes
4. `apply_gravity()` — airborne: `y_vel += 0.21875`
5. `apply_movement()` — `x += x_vel; y += y_vel` (single step)
6. `resolve_collision()` — sensor-based snap/push
7. `update_slip_timer()`
8. `_post_physics()` — state sync (landing, falling)

The critical issue is step 5→6: movement applies velocity in one step, then collision
tries to fix any overlap. At high speeds (>10 px/frame), the player can cross multiple
tiles in a single frame.

## Collision Resolution Mechanics

`resolve_collision()` (terrain.py:740) runs three passes:

**Floor sensors (A/B):**
- On-ground: snap to surface if `|distance| <= 14` (_GROUND_SNAP_DISTANCE)
- Airborne: land if surface found within 16px and y_vel >= 0
- Two-pass: if snap changes quadrant, re-run with new quadrant

**Wall sensors (E/F):**
- Cast from `x ± 10` (WALL_SENSOR_EXTENT) horizontally
- Push player out if distance < 0 (inside wall)
- Angle gate: tiles with angle ≤ 48 or ≥ 208 ignored (floor-range)
- Disabled when moving away from wall
- Only check the tile AT the sensor position + one extension tile

**Ceiling sensors (C/D):**
- Only when airborne or non-normal quadrant
- Push down if inside ceiling, zero upward velocity

## The Bug Mechanism

Reproduction trace (Walker archetype, holds right):

1. **Before entry (f=580-600):** Player is airborne at x≈2878, y≈152, falling with
   increasing velocity. By f=600, speed is ~8.8 x_vel, ~6.6 y_vel.

2. **Traversing gap (f=597-600):** Player crosses cols 188-189 (empty gap) at high
   altitude (y≈222-241), well above the pipe at cols 190+ (surface at y=650).

3. **Landing on pipe roof (f=625):** Player lands on the solid fill at y=486,
   x=3287 (col 205, row 30). The pipe surface acts as ground.

4. **Running across pipe roof (f=625-636):** Speed preserved at 11.16 px/frame.
   Player runs across solid fill at y=480.

5. **Edge of solid fill (f=636):** Ground disappears at col 213 (x=3408-3423).
   Player detaches, becomes airborne.

6. **First clipping (f=638-639):** Moving at 11.3 px/frame + falling, player enters
   the cap/ceiling region of Pipe A. At f=638, x=3433, y=450 (inside row 28 solid).
   At f=639, x=3444, y=462 — first `inside_solid_tile` error.

7. **Bounce oscillation (f=638-660):** Each frame the player alternates between
   landing on a solid surface (which snaps y to surface) and being pushed out,
   then falling back in. The high x_vel carries the player deeper into the pipe.

8. **Trapped in Pipe B (f=660+):** Player eventually reaches Pipe B and gets stuck
   oscillating between ceiling tiles (angle=128, y≈302) and the floor, bouncing
   between y=290 and y=302 indefinitely until frame 3600.

## Why Collision Resolution Fails

1. **No sweep/continuous detection:** `apply_movement()` teleports the player by
   (x_vel, y_vel) in one step. At 11+ px/frame, the player moves more than half
   a tile per frame, easily skipping wall boundaries.

2. **Wall sensor range too narrow:** Wall sensors only check at `x ± 10` from center.
   The wall tiles at the pipe entrance have solid region in cols 10-15 (6px wide).
   At high speed, the player's center passes well beyond col 10 before collision
   runs, placing it deep inside the solid fill.

3. **Conflicting corrections in solid region:** Once inside, floor/ceiling/wall sensors
   all fire. Floor tries to snap to the nearest surface, ceiling pushes down, walls
   push laterally. These corrections conflict, leading to oscillation rather than
   clean ejection.

4. **Air landing threshold too generous:** `_AIR_LAND_DISTANCE = 16` means the player
   can "land" on surfaces that are actually inside solid regions. Combined with the
   regression logic (full tiles regress to check the tile above), the player can
   snap to interior surfaces.

## Invariant Checker: `_check_inside_solid`

Checks player center `(x, y)` against the tile at `(int(x)//16, int(y)//16)`:
- Only fires for `solidity == FULL`
- Computes `solid_top = (ty+1)*16 - height`
- Violation if `y >= solid_top`

This is a center-point check. The player's actual collision box extends ±9 or ±7
pixels (width) and ±20 or ±14 pixels (height) from center.

## Constants

```
STANDING_WIDTH_RADIUS = 9     ROLLING_WIDTH_RADIUS = 7
STANDING_HEIGHT_RADIUS = 20   ROLLING_HEIGHT_RADIUS = 14
WALL_SENSOR_EXTENT = 10       WALL_ANGLE_THRESHOLD = 48
TILE_SIZE = 16                MAX_SENSOR_RANGE = 32
GROUND_SNAP_DISTANCE = 14     AIR_LAND_DISTANCE = 16
GRAVITY = 0.21875             TOP_SPEED = 6.0
```

## Constraints

- The fix must not break existing passing tests (hillside audit, geometry probes, etc.)
- The fix should address the root cause (player entering solid), not just suppress
  the invariant checker
- Pipe tile data is generated by the pipeline — modifying tile_map.json and
  collision.json is an option if the tile layout itself is wrong
- The collision system is sensor-based (Sonic 2 style) and does not use AABB sweeps
