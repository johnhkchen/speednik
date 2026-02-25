# T-007-01 Design: Loop Entry/Exit Ramps

## Problem Summary

The loop circle in `_rasterize_loop` starts at its leftmost point (cx - r, cy) with a vertical tangent. Flat ground ends at the same y-level (cy + r) but at a different x-position. There's no connecting geometry, so the player hits steep tiles and gets blocked by wall sensors.

## Approach A: Analytical Quarter-Circle Arc (Chosen)

Generate ramp tiles by evaluating a quarter-circle arc equation at each pixel column. The arc smoothly transitions from flat ground to the loop's tangent point.

**Entry ramp geometry:**
- Arc center: `(cx - r, cy)` — the leftmost point of the loop circle
- Arc radius: `r_ramp` (default = `r`, the loop radius)
- Arc sweeps from ground level `(cx - r - r_ramp, cy + r)` to tangent point `(cx - r, cy)`
- For each pixel x in `[cx - r - r_ramp, cx - r]`:
  - `dx = x - arc_cx` (negative, since x is left of arc center)
  - `dy = sqrt(r_ramp² - dx²)`
  - `surface_y = arc_cy + dy` (below arc center, curving down to ground)
  - `tangent_angle = atan2(dx, dy)` → mapped to byte angle (0° at ground, ~64° at tangent point)

**Exit ramp geometry (mirror):**
- Arc center: `(cx + r, cy)` — the rightmost point of the loop circle
- Same radius `r_ramp`
- Arc sweeps from tangent point `(cx + r, cy)` to ground level `(cx + r + r_ramp, cy + r)`
- For each pixel x in `[cx + r, cx + r + r_ramp]`:
  - `dx = x - arc_cx` (positive, x is right of arc center)
  - `dy = sqrt(r_ramp² - dx²)`
  - `surface_y = arc_cy + dy`
  - Exit angles: `atan2(-dx, dy)` → mapped to byte angle (~192° at tangent, ~0° at ground)

**Why chosen:** Clean analytical solution. Angles are computed from the arc's exact tangent, guaranteeing smooth transitions. The quarter-circle is the natural geometric complement — it meets the loop circle tangentially at the junction point (both have vertical tangent there), and meets the ground tangentially at the other end (both are horizontal).

## Approach B: Polyline Approximation (Rejected)

Sample the quarter-circle arc at a few points, create line segments, and rasterize with existing `_rasterize_line_segment()`.

**Why rejected:** The per-segment angle computation would produce staircase-like angle jumps between segments. The analytical approach computes a smooth per-pixel angle, which is more accurate and simpler to implement.

## Approach C: Bezier Approximation (Rejected)

Approximate the quarter-circle with a cubic bezier curve, then sample and rasterize.

**Why rejected:** Unnecessary complexity. A quarter-circle has a simple closed-form equation. A bezier approximation introduces error and the sampling/rasterization adds code for no benefit over direct evaluation.

## Design Decisions

### 1. Ramp tiles are `SURFACE_SOLID`, not `SURFACE_LOOP`

Per ticket spec. This means:
- Solidity = `FULL` (from `SOLIDITY_MAP`)
- No `is_loop_upper` needed
- `_fill_interior` will fill below ramp tiles naturally
- Wall sensor angle gate handles angles ≤ 48 gracefully

### 2. Ramps generated BEFORE loop circle

Per ticket spec. The ramp helper is called at the start of `_rasterize_loop()`, before the existing loop segment rasterization. Any tiles at the tangent point that overlap with loop tiles will be overwritten by the loop rasterization, which is correct (loop tiles take priority).

### 3. Ramp radius = loop radius

`r_ramp = r` by default. This produces a natural-looking 1:1 ratio. The ramp spans the same number of tiles horizontally as the loop radius, providing ample transition space.

### 4. Interior fill via shape injection

Ramp tiles need ground fill beneath them. Rather than adding custom fill logic, the ramp tiles will be rasterized as a separate `TerrainShape` with `surface_type=SURFACE_SOLID`, injected into the rasterizer's pipeline so `_fill_interior` handles them automatically.

Actually, simpler: the ramp helper can directly call `_fill_below_ramp()` to fill tiles below each ramp column. This avoids needing a separate shape and is more self-contained.

Simplest of all: after ramp surface tiles are placed, scan each ramp column and fill below with fully-solid tiles (height_array=[16]*16, angle=0). This matches exactly what `_fill_interior` does.

### 5. Angle computation details

**Entry ramp:** At pixel column `px`:
```
dx = px - (cx - r)          # offset from arc center x (negative to zero)
dy = sqrt(r_ramp² - dx²)    # vertical offset (positive, below center)
surface_y = cy + dy          # screen y of surface
tangent = atan2(-dx, dy)     # tangent direction at this point
byte_angle = round(tangent * 256 / (2*pi)) % 256
```

The `-dx` in `atan2(-dx, dy)` accounts for the direction of travel (left to right): the slope rises to the right, so the angle increases from 0 toward 64.

Wait — need to be careful with the engine's angle convention. `_compute_segment_angle` uses `byte_angle = round(-atan2(dy_screen, dx) * 256 / (2*pi)) % 256`. Let me derive from first principles.

For a point on the entry ramp arc at pixel x:
- Surface goes from lower-left to upper-right (ascending)
- In screen coords (y-down), the tangent vector points rightward and upward (dx > 0, dy < 0)
- `atan2(dy, dx)` for this tangent gives a negative angle (pointing into Q4 of standard coords)
- Engine conversion: `byte_angle = round(-atan2(dy_screen, dx_screen) * 256 / (2*pi)) % 256`

For a rising surface with tangent direction (1, -slope):
- atan2(-slope, 1) = negative → negated → positive → gives byte angles 0..64 as slope increases

For the entry ramp, I'll compute the tangent vector from the arc derivative and use the same formula as `_compute_segment_angle`. For the exit ramp, the tangent direction is mirrored.

### 6. No impact on existing code paths

- `_fill_interior` is unchanged — it already fills below `SURFACE_SOLID` tiles
- `_write_collision` is unchanged — ramp tiles are `SURFACE_SOLID` with `FULL` solidity
- Validator: ramp tiles have gradually changing angles, so angle consistency checks should pass between adjacent ramp tiles. At the ramp-to-loop junction, the angles should be close (both near 64° at entry, 192° at exit).

## Implementation Location

A new helper `_rasterize_ramps()` called from the top of `_rasterize_loop()`. The helper:
1. Computes loop geometry (cx, cy, r, r_ramp)
2. Iterates over entry ramp pixel columns, computing surface y and angle analytically
3. Places tiles with `SURFACE_SOLID`, computed `height_array` and `angle`
4. Repeats symmetrically for exit ramp
5. Fills below ramp surface tiles with fully-solid tiles
