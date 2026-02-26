# Research — T-013-03-BUG-03: Speed Demon Pit Death on Skybridge

## Bug Reproduction

Ticket describes death at x≈690, y=928. Actual reproduction shows a different pattern:
- Speed demon now traverses x=0-1590 successfully (the x≈430-700 region is fine)
- **Actual death occurs at x≈1590, y=936** — repeatedly, creating an infinite death loop
- Player respawns at checkpoint x=780, re-dashes, reaches x=1590, dies again
- max_x=1590.9 across all attempts (6 deaths in 1891 frames)

The ticket's evidence may reflect an earlier codebase state before collision fixes in T-013-01/T-013-02.

## Skybridge Stage Layout

- **Grid**: 325 cols x 56 rows (5200px x 896px)
- **Player start**: x=64, y=490
- **Checkpoint 1**: x=780, y=490
- **Checkpoint 2**: x=3980, y=490
- **Goal**: x=5158, y=482
- **Pit death**: y > 896 + 32 = 928

### Bridge Structure

The stage consists of repeating bridge-slope segments along row 31 (y=496):

| Segment | Bridge (TOP_ONLY) | Slope/Pillar (FULL) |
|---------|-------------------|---------------------|
| 1 | cols 0-10 (x=0-176) solid ground | |
| 2 | cols 11-24 (x=176-400) bridge | cols 27-28 gap |
| 3 | cols 29-35 (x=464-576) bridge | cols 36-37 gap |
| 4 | cols 39-49 (x=624-800) bridge | cols 50-51 FULL transition |
| 5 | cols 76-99 (x=1216-1584) bridge | cols 100-101 FULL wall |
| 6 | cols 126-149 (x=2016-2384) bridge | cols 150-152 FULL wall |
| 7 | cols 176-249 (x=2816-3984) bridge | |
| 8 | cols 250+ (x=4000+) solid ground to goal | |

### Springs (all spring_up, y_vel = -10.0)

| # | x | y | Tile Col | Bridge Segment |
|---|---|---|----------|----------------|
| 1 | 304 | 608 | 19 | seg 2 |
| 2 | 440 | 608 | 27 | gap between seg 2-3 |
| 3 | 592 | 608 | 37 | gap between seg 3-4 |
| 4 | 1200 | 608 | 75 | before seg 5 |
| 5 | 2016 | 608 | 126 | start of seg 6 |
| 6 | 2832 | 608 | 177 | start of seg 7 |
| 7 | 3808 | 692 | 238 | within seg 7 |

## Death Zone Analysis: x=1590 (cols 99-100)

### Collision Grid (rows 30-38, cols 93-107)
```
Row 30 (y=480):  . . . . . . . . . . . . . . .     (air)
Row 31 (y=496):  1 1 1 1 1 1 1 2 2 . . . . . .     (bridge → wall)
Row 32 (y=512):  1 1 1 1 1 1 1 2 2 2 2 . . . .     (bridge → slope)
Row 33 (y=528):  . . . . . . . 2 2 2 2 2 2 . .     (pillar + slope)
Row 34 (y=544):  . . . . . . . 2 2 2 2 2 2 2 2
Row 35 (y=560):  . . . . . . . 2 2 2 2 2 2 2 2
Row 36-42:       . . . . . . . 2 2 2 2 2 2 2 2     (solid pillar)
                 93             100                   ← columns
```

### Tile Map at Transition (col 100, row 31)
```
tile_map[31][100]: type=1, height_array=[12,11,11,10,10,9,9,8,8,7,7,6,6,5,5,4], angle=0
collision[31][100] = 2 (FULL)
```

**Critical mismatch**: tile_map says type=1 (TOP_ONLY) but collision.json says 2 (FULL).

The collision.json is what the physics engine uses. The FULL tile at col 100, row 31 acts
as a wall: the wall sensor detects the FULL tile and pushes the player back, zeroing x_vel.

### Death Sequence
1. Frame 170-200: Speed demon rolling at ~7.5px/frame on bridge (row 31, cols 93-99)
2. Frame 204: x=1583.1, x_vel=11.87 — approaching col 100 (x=1600)
3. Frame 205: x=1590.0, x_vel=0.0 — **wall sensor hit at col 100 boundary, x_vel zeroed**
4. Frame 205-235: Falling straight down with x_vel=0 (no horizontal movement)
5. Frame 236: y=941.2, pit death triggered

The player's x is clamped at 1590.0 (wall pushback from the FULL tile at x=1600), then
falls through the open air below the TOP_ONLY bridge at row 31.

### Why the Bridge Has No Floor Below

Cols 93-99 have TOP_ONLY tiles at rows 31-32 only. Below (rows 33-55) is completely empty.
This is by design — it's a "sky bridge" that the player walks on top of. But if the player
loses horizontal momentum (hits a wall), they fall through the gap below.

## Speed Demon Archetype Behavior

- Spindash charges for 3 frames → spinrev ≈ 2.0 (after decay)
- Release speed: 8 + floor(2.0/2) = **9.0 px/frame**
- Rolls with friction 0.0234375/frame, decelerating to ~7.5 by x=800
- Re-dashes when ground_speed < 2.0 (after reaching checkpoint at x=780)
- Second dash carries through bridge segment 5 (cols 76-99)
- Hits FULL wall at col 100, dies

## Root Cause

**collision.json has FULL (2) at cols 100-101, row 31** where the terrain should transition
from the bridge level to a downhill slope. The tile_map shows a slope tile (angle=237,
height_array descending from 12 to 4), suggesting the intent was a smooth slope transition.
But the collision solidity is FULL instead of TOP_ONLY, creating an impassable wall.

The same pattern repeats at cols 150 (x=2400) and potentially other bridge-to-slope
transitions.

## Adjacent Files

- `speednik/stages/skybridge/collision.json` — collision grid (needs fix)
- `speednik/stages/skybridge/tile_map.json` — tile height/angle data
- `speednik/stages/skybridge/entities.json` — springs, rings, checkpoints
- `speednik/terrain.py` — collision resolution, sensor casts
- `speednik/simulation.py` — pit death logic
- `speednik/qa.py` — speed demon archetype, audit framework
- `speednik/constants.py` — PIT_DEATH_MARGIN=32, SPRING_UP_VELOCITY=-10.0
