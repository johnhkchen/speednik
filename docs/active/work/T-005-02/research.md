# Research: T-005-02 hillside-loop-collision-fix

## Problem Summary

The 360° loop in Hillside Rush Section 5 is vertically misaligned. The loop circle
center is at y=380 (bottom at y=508), but ground level in the loop zone is y=636.
This creates a 128px gap between the loop bottom and the ground, making the loop
unreachable during normal gameplay.

## SVG Source: `stages/hillside_rush.svg`

### Section 5 (lines 219–272)

Four collision shapes define the loop zone:

1. **Approach polygon** (lines 227–230): slopes from y=636 down to y=508 with
   intermediate points at (3300,600), (3400,560), (3460,520), (3472,508).
   Fills down to y=720.

2. **Loop circle** (line 233): `cx="3600" cy="380" r="128"`, green stroke.
   - Top: y = 380 − 128 = 252
   - Bottom: y = 380 + 128 = 508
   - Left edge: x = 3600 − 128 = 3472
   - Right edge: x = 3600 + 128 = 3728

3. **Exit polygon** (lines 236–239): mirrors approach, slopes from y=508 back up
   to y=636 with points (3740,520), (3800,560), (3900,600), (4000,636).

4. **Ground-beneath-loop polygon** (lines 242–244): rectangle from (3472,508)
   to (3728,720). This fills the 128px gap between loop bottom (508) and the
   approach/exit connection point, creating solid ground where the loop should
   have its bottom arc.

### Ring Entities (lines 247–272)

- **ring_131–ring_150** (20 rings): circular pattern around center (3600, 380).
  Ring Y-values range from 324 (top) to 476 (bottom). All centered on the
  current (incorrect) loop center.

- **ring_151–ring_155** (5 approach rings): Y-values from 622 down to 540,
  following the slope from ground level to loop bottom. These also follow the
  incorrect slope.

## SVG-to-Stage Pipeline: `tools/svg2stage.py`

### Circle Processing

`_parse_circle()` (line 538): green-stroked circles become `TerrainShape` with
`is_loop=True`. The circle is sampled as perimeter segments via
`_ellipse_perimeter_segments()` at 16px intervals (~50 sample points for r=128).

### Loop Rasterization

`_rasterize_loop()` (line 745): marks tiles as `SURFACE_LOOP` (type 5) and computes
per-tile angles. Upper-half tiles (sy < cy) get `is_loop_upper=True`. The loop
center `cy` determines the upper/lower split.

### Polygon Processing

Standard polygons rasterize as `SURFACE_SOLID` (type 1). The approach/exit slopes
and ground-fill rectangle all produce solid collision tiles.

## Generated Stage Data: `speednik/stages/hillside/`

### collision.json

Loop region occupies tile rows 15–32 (y=240–512), columns 217–233 (x=3472–3728).
The loop perimeter appears as type-2 (FULL) collision values forming a ring pattern.
Below (ty=31–32), the ground-beneath-loop polygon creates solid fill.

### tile_map.json

- Loop tiles: type 5 (SURFACE_LOOP) with angles 0–251°
- Ground-fill tiles (ty=31–32): type 1 (SURFACE_SOLID), angle 0, height=[16,16,16,16]
- Approach/exit slopes: angle values 32–64° on left, 192–232° on right

### validation_report.txt (234 lines)

**Loop-specific issues:**
- Angle inconsistencies at loop-to-ground transitions (rows 30–31): diffs up to 113°
- Angle inconsistencies at approach/exit column edges (tx=216–218, 232–234): 64° diffs
- 12px impassable gaps at columns 220, 229 at y=496 (loop bottom to ground transition)
- Multiple 1px gaps at columns 217, 218, 231, 232 (loop side walls)

Many of the 234 validation warnings are from other sections, but the loop zone
contributes significantly to the angle inconsistencies (rows 31–44, columns 216–234).

## Test Coverage: `tests/test_hillside.py`

### Loop Tests (TestLoopGeometry class, lines 106–128)

Two tests exist:
1. `test_loop_tiles_exist`: scans ty=15–32, tx=218–233 for any non-None tiles.
   Currently checks the old loop position. Will need range adjustment.
2. `test_loop_has_varied_angles`: verifies ≥4 distinct angle values in same region.
   Also needs range adjustment.

Both tests hardcode the current (incorrect) loop center y=380. After the fix
(cy=508), the loop will span y=380–636 instead of y=252–508, shifting the tile
rows down by 8 rows (128px / 16px per tile).

### Other Tests

Entity counts, player start position, level dimensions — these should be unaffected
by the loop fix since only collision geometry and ring positions change.

## Key Constraints

1. The SVG uses a coordinate system where y increases downward. Ground level = y=636.
2. The pipeline tool `svg2stage.py` is run manually; it is not part of the build.
3. The approach rings (ring_151–155) slope from ground to loop bottom. If the loop
   bottom moves to y=636, the approach is flat and these rings need Y adjustment.
4. The loop rings (ring_131–150) are centered on the loop. If cy moves from 380 to
   508, all 20 rings need their Y coordinates shifted by +128.
