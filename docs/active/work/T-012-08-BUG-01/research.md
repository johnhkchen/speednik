# Research: T-012-08-BUG-01 — Hillside Loop Not Traversable

## Problem Statement

The hillside stage loop traps the player in an oscillation at x=3443-3449 (tx=215),
y=571-589 (ty=35-36). The player enters Q1 (right-wall angles 33-96) but never
advances to Q2 (ceiling, 97-160) and never exits the loop region.

## Loop Geometry Overview

The hillside loop spans tile columns tx=217-233 (pixel x=3472-3744). It is a
hand-placed circular loop with ~136px radius, centered approximately at
(tx=225, ty=31) = pixel (3600, 496).

### Tile Layout

**Approach ramp** (tx=212-216, type=1 regular tiles, sol=2 FULL):
- tx=212 ty=38: angle=21 → tx=213 ty=38: angle=27 (Q0 approach)
- tx=214 ty=37: angle=34 → tx=215 ty=37: angle=35 (Q1 entry)
- tx=215 ty=36: angle=41 → tx=215 ty=35: angle=43 (Q1 steepening)
- tx=216 ty=35: angle=47 → tx=216 ty=34: angle=52 → tx=216 ty=33: angle=58 (Q1)

**Loop right wall** (tx=217-218, type=5 loop tiles):
- ty=35: angle=82-87 (Q1, upper right wall)
- ty=34: angle=77 (Q1)
- ty=33: angle=72 (Q1)
- ty=32: angle=67 (Q1)
- ty=31: angle=61 → ty=30: angle=56 → ty=29: angle=51 → ty=28: angle=46 (Q1)

**Loop top** (tx=219-229, type=5):
- Angles smoothly transition: 31→26→20→15→10→5→0→251→246→241→236→230→225
- These are all Q0 (0-32) or Q0 (224-255) — the ceiling tiles never enter Q2!

**Loop left wall** (tx=230-233, type=5):
- Angles: 220→215→210→205→200→195→184→179→174→169→164 (Q3)

**Loop inner ceiling** (tx=219-221 and tx=228-230, ty=37-38, type=5):
- tx=219 ty=37: angle=92 (Q1), tx=220 ty=37: angle=102 (Q2)
- tx=220 ty=38: angle=102 (Q2), tx=221 ty=38: angle=108 (Q2)
- tx=228 ty=38: angle=143 (Q2), tx=229 ty=38: angle=148 (Q2)
- tx=230 ty=37: angle=154 (Q2), tx=229 ty=37: angle=154 (Q2)

### Angle Quadrant Distribution

The loop outer arc has angles in Q0, Q1, Q3 only — no Q2 tiles on the outer arc.
Q2 tiles (97-160) exist only on the inner ceiling surface (ty=37-38).

In Sonic 2, the player traverses the loop's INNER surface (inside of the circle).
The current hillside loop has the outer arc (top of loop at ty=23-24) with ceiling-
position tiles that have Q0 angles (flat/near-flat), meaning the sensor system
treats them as floor tiles, not ceiling tiles.

## Root Cause Analysis

### The Oscillation Mechanism

Diagnostic simulation reveals the frame-by-frame failure:

1. **Frame 35**: Player at x=3432, angle=41 (Q1). Floor sensors switch to
   RIGHT-cast mode. Player snapped to the right-wall surface.

2. **Frame 37**: Player at x=3443, angle=47 (Q1). Correctly on the ramp surface.

3. **Frame 38**: Player at x=3447, angle=52 (Q1). Floor sensor reports
   distance=-5.0 (inside solid). Player y jumps from 575→582 — snapped BACKWARD.

4. **Frames 39+**: Oscillation between ty=35 (angle=47) and ty=36 (angle=41/47).
   The floor sensor alternately snaps the player up and down.

The oscillation occurs because:

- **Q1 floor sensors cast RIGHT** (not down). At tx=215 ty=35 (angle=43/47),
  the rightward sensor hits the steep ramp/loop-wall tiles at tx=216-217.
- The rightward sensor finds the surface at different distances depending on
  exact y position, causing the snap to alternate between two tile rows.
- The approach ramp tiles (type=1, FULL solidity) have Q1 angles that trigger
  wall-mode sensors, but their height arrays represent a slope surface — they're
  not actually vertical walls.

### Why the Player Never Reaches the Loop

The approach ramp angles (41-58 at tx=215-216) all fall in Q1 (33-96), which
activates right-cast floor sensors. But these ramp tiles are shaped as slopes
(gradual height progression), not as vertical walls. The RIGHT-cast sensor
interprets the slope surface incorrectly, producing oscillating snap distances.

The player x never advances past ~3449 (tx=215) because:
1. In Q1, movement is computed from ground_speed via cos/sin of a Q1 angle
2. The y-velocity component is large (moving upward along the "wall")
3. But the sensor system keeps snapping the player back, zeroing y_vel

## Comparison with Synthetic build_loop()

The synthetic `build_loop()` works because:
1. It uses angular sampling to produce smooth sub-pixel height progressions
2. Its ramp tiles transition gradually from Q0 into Q1 with matching height arrays
3. The entry ramp uses a quarter-circle arc with correct wall geometry
4. Loop tiles use SURFACE_LOOP type, which exempts them from wall sensor blocking

The hillside loop fails because:
1. The approach ramp is separate non-loop tiles (type=1) with Q1 angles
2. These tiles have slope-shaped height arrays, not wall-shaped
3. The Q0→Q1 transition happens abruptly at the ramp rather than gradually
4. The floor sensor direction switches from DOWN to RIGHT but the tile
   geometry doesn't support rightward surface detection properly

## Key Files

| File | Relevance |
|------|-----------|
| `speednik/terrain.py` | Sensor casts, floor/ceiling detection, resolve_collision |
| `speednik/physics.py` | Movement decomposition, slope factor, byte angle math |
| `speednik/grids.py` | Synthetic build_loop() that works correctly |
| `speednik/level.py` | Loads tile_map.json into Tile objects |
| `speednik/stages/hillside/tile_map.json` | The hand-placed loop tiles |
| `speednik/stages/hillside/collision.json` | Solidity values per tile |
| `speednik/constants.py` | Sensor radii, angle thresholds |
| `tests/test_loop_audit.py` | Test harness for loop traversal |
| `tools/svg2stage.py` | Pipeline that generates tile_map.json from SVG |

## Constraints

- The `build_loop()` synthetic loops work for radius 48, confirming the physics
  engine CAN traverse loops. The fix is in the hillside tile data or the
  transition from approach ramp to loop tiles.
- Changing the physics engine's sensor system would risk breaking synthetic loops.
- The approach ramp tiles are shared geometry with the visible hillside terrain;
  changing their angles/solidity could break non-loop collision.
- The inner ceiling tiles (ty=37-38) DO have Q2 angles (102-154), which means
  the loop data contains a valid inner traversal path — it's just that the
  player can't reach it through the approach ramp.
