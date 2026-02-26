# Research — T-012-03-BUG-01: pipeworks-slope-wall-blocks-progress

## Problem

Tile column 32, rows 10–16 in the Pipeworks stage have `angle=64` (right-wall
quadrant). A diagonal slope of `angle=32` tiles leads directly into this column.
When the player walks up the slope and reaches column 32, the angle jumps from
32 (floor quadrant boundary) to 64 (wall quadrant), triggering wall-mode
physics that zero out horizontal velocity and block all forward progress.

All jumping/dashing archetypes stall before x=520. Walker and Wall Hugger take a
lower path and bypass this obstacle entirely (they hit a different bug at
x≈3095, tracked in T-012-03-BUG-02).

## Tile Data

### Column 32 wall tiles (angle=64)

```
tile(32,10): angle=64, type=1, sol=2, h=[0,0,0,0,0,0,0,0,16,16,16,16,16,16,16,16]
tile(32,11): angle=64, type=1, sol=2, h=[0,0,0,0,0,0,0,0,16,0,0,0,0,0,0,0]
tile(32,12): angle=64, type=1, sol=2, h=[1,2,2,4,4,6,7,7,16,0,0,0,0,0,0,0]
tile(32,13): angle=64, type=1, sol=2, h=[16]*16  (fully solid)
tile(32,14): angle=64, type=1, sol=2, h=[16]*16  (fully solid)
tile(32,15): angle=64, type=1, sol=2, h=[16]*16  (fully solid)
tile(32,16): angle=64, type=1, sol=2, h=[16]*16  (fully solid)
```

Rows 10–12 form the top of the left pipe wall (partial height arrays showing a
wall edge). Rows 13–16 are fully solid underground/interior tiles.

### Slope approach tiles (angle=32)

```
tile(24,20): angle=32, type=3, sol=2, h=[1,1,3,4,4,6,6,8,9,10,11,11,13,14,15,16]
tile(25,19): angle=32, type=3, sol=2, h=[0,2,2,4,5,5,7,7,9,10,11,12,12,14,15,16]
tile(26,18): angle=32, type=3, sol=2, h=[1,1,3,3,5,6,6,8,8,10,11,12,13,13,15,16]
tile(27,17): angle=32, type=3, sol=2, h=[1,2,2,4,4,6,7,7,9,9,11,12,13,14,14,16]
tile(28,16): angle=32, type=3, sol=2, h=[0,2,3,3,5,5,7,8,9,10,10,12,13,14,15,15]
tile(29,15): angle=32, type=3, sol=2, h=[1,1,3,4,4,6,6,8,9,10,11,11,13,14,15,16]
tile(30,14): angle=32, type=3, sol=2, h=[0,2,2,4,5,5,7,7,9,10,11,12,12,14,15,16]
tile(31,13): angle=32, type=3, sol=2, h=[1,1,3,3,5,6,6,8,8,10,11,12,13,13,15,16]
```

Each tile rises ~16px over 16px (45° slope, matching angle=32). The slope runs
from pixel x=384 (col 24) to x=512 (col 32).

### Neighboring underground tiles (angle=0, correct)

```
tile(31,14): angle=0, type=3, sol=2, h=[16]*16
tile(31,15): angle=0, type=3, sol=2, h=[16]*16
tile(32,17): angle=0, type=3, sol=2, h=[16]*16  (below the pipe)
```

Tiles below the surface at columns 30–31 correctly use `angle=0` for fully
solid interior tiles. Column 32 rows 13–16 are the same geometry (fully solid,
`h=[16]*16`) but incorrectly use `angle=64`.

### Pipe structure context

Column 32 is the **left wall** of a horizontal pipe (cols 32–50). Column 50 is
the right wall (also angle=64). The pipe interior (cols 33–49) uses angle=0 for
floor tiles and angle=128 for ceiling tiles at row 16.

Row 9 at col 32 is null (empty air above the pipe).

## Physics Engine Behavior

### Angle → quadrant mapping (`terrain.py:100`)

- Quadrant 0 (floor): angle 0–32 or 224–255
- Quadrant 1 (right wall): angle 33–96
- Quadrant 2 (ceiling): angle 97–160
- Quadrant 3 (left wall): angle 161–223

`angle=32` is at the upper boundary of quadrant 0 (floor). `angle=64` is solidly
in quadrant 1 (wall). When the player transitions from a tile with angle=32 to
one with angle=64, `get_quadrant()` returns 1 instead of 0, triggering wall-mode
sensor casts that block horizontal movement.

### WALL_ANGLE_THRESHOLD (`constants.py:123`)

`WALL_ANGLE_THRESHOLD = 48`. Tiles with byte angle ≤ 48 or ≥ 208 are
considered floor-range. angle=64 exceeds this threshold.

## Similarity to T-012-02-BUG-01

The Hillside bug was identical in pattern: tile (37,38) had `angle=64` where
the height array described a gentle slope (correct angle=2). Fix: change the
single angle value in tile_map.json. No code changes needed.

Pipeworks is more complex: an entire column has angle=64. But the root cause is
the same — fully solid underground tiles (`h=[16]*16`) at rows 13–16 have
angle=64 where they should have angle=0. These tiles are buried beneath the
surface and the player walks over the top of them; the top surface is flat.

## Affected Files

| File | Role |
|------|------|
| `speednik/stages/pipeworks/tile_map.json` | Tile data with angles |
| `speednik/stages/pipeworks/collision.json` | Solidity (not changing) |
| `speednik/terrain.py` | Collision engine (not changing) |
| `speednik/simulation.py` | Headless sim for testing |
| `tests/test_terrain.py` | Tile data regression tests |
| `tests/test_simulation.py` | Integration tests |
| `tests/test_audit_pipeworks.py` | xfail audit tests (BUG-01 refs) |

## Key Constraint

The pipe wall tiles at rows 10–12 have genuine wall geometry (partial height
arrays with solid pixels on one side). The fix must distinguish between:
- Rows 10–12: actual pipe wall entrance — these may legitimately use angle=64
  for the vertical wall face
- Rows 13–16: fully solid underground tiles — these must use angle=0

However, row 12 (`h=[1,2,2,4,4,6,7,7,16,0,0,0,0,0,0,0]`) has a slope in its
left half that merges into the wall. This tile transitions from slope to wall
within a single tile. Its left-half height array resembles the angle=32 slope
approach. The player walks on the left half of this tile (the slope surface)
before hitting the wall at pixel column 8. The angle=64 on this tile causes
premature wall-mode activation when the player's sensors read it.

Row 11 (`h=[0,0,0,0,0,0,0,0,16,0,0,0,0,0,0,0]`) is a single-pixel-wide wall
at pixel column 8 — a thin vertical surface. Row 10 has the right half solid
(`h=[0...,16,16,16,16,16,16,16,16]`), forming the pipe entrance cap.

The player approaches from below-left on the slope and the first fully-solid
tile they encounter is (32,13) — this is the critical blocker. Rows 10–12 are
above the slope surface and should not be contacted during normal rightward
traversal.
