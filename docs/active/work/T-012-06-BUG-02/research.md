# Research: T-012-06-BUG-02 — large-loop-exit-overshoot

## Bug Summary

For synthetic loops with radius >= 64, the player never lands on the exit flat
tiles after traversing the loop. The ticket description says the player "overshoots
the exit region entirely", but the actual failure mode is different from what was
expected.

## Actual Failure Mode (Diagnosed)

The player does NOT overshoot the exit. Instead, the player **detaches from the
loop surface during the Q2→Q3 transition** (ceiling → left wall) and falls
BACKWARD, landing on the approach tiles behind the loop. The player then runs
backward with negative ground_speed, eventually re-approaching the loop, but
never successfully completing it.

### r=64 Timeline

| Frame | Position | Angle | Quadrant | Event |
|-------|----------|-------|----------|-------|
| f20 | (271, 306) | 255 | Q0 | Last ground before ramp entry |
| f23 | (304, 300) | 240 | Q0 | Lands on loop bottom |
| f31 | (385, 273) | 59 | Q1 | Enters right wall |
| f39 | (354, 207) | 123 | Q2 | Enters ceiling |
| f45 | (295, 216) | 153 | Q2 | Last on-ground frame |
| f46 | (287, 222) | 0 | Q0 | **Detaches — goes airborne** |
| f56 | (208, 306) | 0 | Q0 | Lands on approach flat (BACKWARD) |

### Root Cause: Sensor B Falls Into Empty Tile

At f45, the player is at (294.9, 216.0), angle=153 (Q2). Floor sensors in Q2
cast UP from `(x ± w_rad, y - h_rad)`:

- Sensor A: (301.9, 202.0) → tile (18, 12) — has ceiling tile, finds surface
- Sensor B: (287.9, 202.0) → tile (17, 12) — **no tile exists**

Tile (17, 12) spans y=192-208. The loop surface at tx=17 starts at ty=13
(y=208-224). The sensor at y=202 is above the surface tile — it's in the row
ABOVE where the ceiling surface lives. Since (17, 12) is empty and (17, 11) is
also empty, the UP-cast finds nothing.

### Why No Tile at (17, 12)?

The loop center is at (336, 256) with radius 64. The left edge of the circle
is at x=272, which is exactly the start of tile column 17. At theta_byte ≈ 153
(where the player detaches), the circle point is around (283, 219) — this is in
tile (17, 13), not (17, 12). The ceiling surface at tx=17 is at y ≈ 208-224,
which falls entirely within tile row 13.

There is no surface above y=208 at tx=17 because the circle doesn't extend
there. The sensor overshoots UP past the surface.

### Player Drift Inward

The player's center tracks at 50-57px from the loop center vs the 64px radius.
This 7-14px inward drift is systematic — the snap logic positions the player's
bottom edge at the surface, so the center is offset by the height_radius (14px
for rolling). The drift means floor sensors in Q2 (which cast from y - h_rad)
reach further above the surface than expected.

For r=48, the same drift occurs (~32-36px from center vs 48px radius) but the
smaller loop means tiles are more densely packed relative to the sensor offset,
so sensors still find surfaces.

## Key Codebase Components

### Loop Geometry: `speednik/grids.py` — `build_loop()`

Lines 294-361: Angular iteration around circumference produces tiles with
traversal angles. The circle is sampled at sub-pixel resolution.

- **Loop circle range**: x ∈ [loop_start, loop_end) where loop_start =
  approach_px + ramp_radius, loop_end = loop_start + 2*radius
- **Pixel clipping** (line 318): `if px < loop_start or px >= loop_end: continue`
  This clips the circle to a strict horizontal range. For the leftmost and
  rightmost columns, this means only partial coverage.

Lines 362-391: Exit ramp (quarter-circle arc) placed at ground_row only.

Lines 393-400: Flat exit tiles starting after ramp.

### Floor Sensors: `speednik/terrain.py`

`find_floor()` (lines 623-658): Dispatches A/B sensors based on quadrant.
Q2 sensors: A at (x+w_rad, y-h_rad), B at (x-w_rad, y-h_rad), casting UP.

`_sensor_cast_up()` (lines 235-361): Checks current tile, tile above, and
(BUG-01 fix) tile below as fallback. The fallback checks the tile BELOW the
sensor start position — but in this case the tile below (17, 13) has the
surface, and the sensor is in tile (17, 12). The fallback should find this...

### Landing Logic: `resolve_collision()` (lines 922-957)

Ground: detaches when `floor_result.found` is false or distance > 14px.
Airborne: lands when `floor_result.found and y_vel >= 0 and distance <= 16px`.

The detach at f46 happens because the floor sensor returns found=False (no
surface within range in Q2 direction). The player's angle resets to 0 (Q0)
and it becomes airborne with negative x_vel.

### Physics: `calculate_landing_speed()` (lines 300-332)

When the player lands at f56 on the approach flat (angle=0, flat range), it
sets ground_speed = x_vel = -7.47. This negative speed sends the player
backward.

## Comparison: r=48 (Works) vs r=64 (Fails)

| Metric | r=48 | r=64 |
|--------|------|------|
| Drift from center | ~12-16px | ~7-14px |
| Drift/radius ratio | 25-33% | 11-22% |
| Completes Q2→Q3 | Yes | No |
| Left wall tiles at ceiling height | (18,12) exists | (17,12) missing |
| Sensor overshoot past surface | Within tile bounds | Past tile boundary |

The critical difference: r=48's loop circle is small enough that sensor
overshoot stays within tiles that contain surface data. r=64's larger circle
means the Q2→Q3 transition zone (upper-left) has a tile gap where sensors
find nothing.

## Key Constraint

The `_sensor_cast_up()` BUG-01 fallback already checks the tile BELOW the
sensor position when current + above are empty. This should find (17, 13).
Need to verify whether this fallback is actually triggering and what it
returns.

## Further Investigation: height==0 Blind Spot

After the BUG-01 fallback was confirmed working for the empty-tile case (sensor
B in tile (17,12) which is None), a second failure was found on the NEXT frame.

At f45→f46, after the player moves, sensor A lands at (293.6, 207.8) in tile
(18, 12). This tile **exists** with `height_array[5] = 0` at the sensor column.
The code enters the `height == 0` branch, checks tile above (18, 11) → None,
and returns `found=False`. But tile (18, 13) below has `height_array[5] = 16`
with `solid_top = 208` — just 0.2px below the sensor.

The `_sensor_cast_up()` function's `height == 0` branch only checked tile above,
not tile below. This is a blind spot: the tile exists but has no solid at the
sensor column, and the surface is in the tile below.

## Secondary Issue: Exit Tile Coverage

For r=96, even after fixing the sensor blind spot (allowing full loop traversal),
the player exits the loop with a high-speed ballistic arc that overshoots the
exit flat tiles. The exit tiles (15 tiles × 16px = 240px) are insufficient for
r=96's trajectory, which requires ~500px of landing zone.

## Summary of Findings

1. The bug manifests as detachment during Q2→Q3 — the player never reaches the
   exit for r=64 and r=96
2. Primary cause: `_sensor_cast_up()` `height==0` branch doesn't check tile
   below. When a tile exists with h[col]=0, it only checks above, missing the
   surface in the tile below.
3. Secondary cause: exit flat tiles are too few for large-radius loops where the
   player exits with a high-speed ballistic trajectory
4. After detaching, the player falls backward with negative x_vel and never
   returns to the exit region
5. For r=96, the same sensor pattern occurs at a different point in the arc
6. r=128 has a separate issue (loop trapping) beyond the scope of this ticket
