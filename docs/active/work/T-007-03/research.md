# T-007-03 Research: profile2stage Loop Entry/Exit Ramps

## Scope

Add quarter-circle transition ramp tiles before and after the loop circle in `_rasterize_loop` within `tools/profile2stage.py`. The svg2stage pipeline (T-007-01) already has this logic; this ticket ports the concept to the cursor-based profile pipeline.

## Relevant Files

### Primary
- `tools/profile2stage.py` — The profile-to-stage pipeline. Contains `Synthesizer._rasterize_loop()` at lines 627–672.
- `tests/test_profile2stage.py` — Test suite. `TestLoopSegment` class at lines 1030–1217 with 7 existing loop tests.

### Reference
- `tools/svg2stage.py` — Contains `Rasterizer._rasterize_ramps()` at lines 807–923, the reference implementation from T-007-01.

### Shared Components (imported from svg2stage)
- `SURFACE_SOLID` (type 1), `SURFACE_LOOP` (type 3), `SURFACE_TOP_ONLY` (type 2)
- `TILE_SIZE` = 16
- `TileData`, `TileGrid`, `Validator`, `StageWriter`, `Entity`

## Current `_rasterize_loop` Behavior

```
Input:  cursor_x, cursor_y, seg.radius
Center: cx = cursor_x + radius, cy = cursor_y - radius
Range:  [cursor_x, cursor_x + 2*radius)
Output: cursor_x += 2*radius, cursor_y unchanged, cursor_slope = 0.0
```

For each pixel column in [start_col, end_col):
1. Compute dx from center, dy = sqrt(r² - dx²)
2. Place bottom arc pixel at (px, cy + dy) as SURFACE_LOOP
3. Place top arc pixel at (px, cy - dy) as SURFACE_LOOP with is_loop_upper=True
4. Fill column below bottom arc via `_fill_column_below`
5. After all columns: `_fill_below_loop` fills remaining gaps

**Problem:** No ramp tiles exist. The loop starts abruptly at the leftmost pixel column with an angle of ~90° (tangent at 3 o'clock on the circle). The player transitions instantly from flat ground (angle 0°) to the loop tangent — a huge discontinuity.

## Reference Implementation: svg2stage `_rasterize_ramps`

### Geometry
- **Entry ramp**: Quarter-circle arc centered at `(cx - r, cy)` (loop's leftmost point)
  - X range: `[cx - r - r_ramp, cx - r)`
  - Surface equation: `sy = cy + sqrt(r_ramp² - (px - arc_cx)²)`
  - At x = cx - r - r_ramp: sy = cy + 0 ≈ ... but actually the arc starts near ground_y
  - At x = cx - r: sy approaches cy (loop tangent point)

- **Exit ramp**: Quarter-circle arc centered at `(cx + r, cy)` (loop's rightmost point)
  - X range: `(cx + r, cx + r + r_ramp]`
  - Same equation, mirrored

### Tile Properties
- `surface_type = SURFACE_SOLID` (not SURFACE_LOOP)
- `is_loop_upper` is NOT set (these are normal ground tiles)
- Height arrays computed analytically from arc equation
- Angles computed from consecutive arc surface points

### Ground Fill
- Finds topmost ramp tile per tile-column, fills all rows below with fully-solid tiles.

## Differences: svg2stage vs profile2stage

| Aspect | svg2stage | profile2stage |
|--------|-----------|---------------|
| Model | Shape-based (SVG paths) | Cursor-based (segments) |
| Loop center | From SVG circle center attribute | Computed: `(cursor_x + r, cursor_y - r)` |
| Ground level | `cy + r` (bottom of circle) | `cursor_y` (same as cy + r) |
| Pixel placement | `_place_ramp_pixel` (custom) | `_set_surface_pixel` (existing method) |
| Angle computation | `_compute_segment_angle(Point, Point)` | Inline `math.atan2` with byte-angle formula |
| Ground fill | Custom per-column ramp fill | `_fill_below` (existing method covers ramp range) |
| Cursor tracking | None (shape-based) | Must advance cursor by `r_ramp + 2*radius + r_ramp` |

## Key Methods Available in Synthesizer

- `_set_surface_pixel(col, y, angle)` — Sets one pixel column with SURFACE_SOLID, computes height from tile bottom.
- `_fill_below(start_col, end_col)` — Fills tiles below topmost surface tile in each column.
- `_fill_column_below(col, y)` — Fills a single column below y.
- `_fill_below_loop(start_col, end_col)` — Fills below lowest SURFACE_LOOP tile per column.
- `_set_loop_pixel(col, y, angle, is_upper)` — Sets one pixel column with SURFACE_LOOP.

## Cursor Integration Requirements

Current: `cursor_x += 2 * radius`
New: `cursor_x += r_ramp + 2 * radius + r_ramp`

The `_build_segment_map` at line 292 uses `seg.len` for advancing, which is `2 * radius`. This will need updating too — otherwise entity/overlay position resolution will be wrong. The segment len should become `r_ramp + 2 * radius + r_ramp`.

**Wait**: `seg.len` is set during parsing at line 135: `seg_len = 2 * radius`. If we change this, it affects segment map and entity resolution. The cleanest approach: update `seg.len` to include ramp extents so everything is consistent.

## `_build_segment_map` Impact

Line 298: `seg_map[seg.id] = (cx, cy, seg.len)` then `cx += seg.len`.
If `seg.len` includes ramps, segment map is automatically correct. Entity offset_x references within the segment would be relative to the segment start (including entry ramp), which is the natural expectation.

## Existing Tests to Update

1. `test_loop_cursor_advance` (line 1119) — asserts `cursor_x == 2 * radius`. Must change to `4 * radius`.
2. `test_loop_interior_hollow` (line 1058) — center calculation `cx = 128 + radius`. With ramps, the flat-before segment (128px) plus entry ramp (radius px) shifts the loop circle start. Center becomes `128 + radius + radius = 128 + 2*radius`.
3. `test_loop_upper_lower_solidity` (line 1077) — same center shift.
4. `test_loop_ground_fill` (line 1135) — same center shift.
5. `test_loop_angle_variation` (line 1153) — should still pass (more tiles with varying angles).
6. `test_loop_no_gap_errors` (line 1047) — should pass (ramps reduce gaps).
7. `_make_loop_profile` helper (line 1031) — width calculation needs `4 * radius` not `2 * radius`.

## Angle Computation

profile2stage uses inline byte-angle computation:
```python
angle = round(-math.atan2(rise, run) * 256 / (2 * math.pi)) % 256
```

For ramp arc at pixel x with arc center at arc_cx:
```python
sy = cy + sqrt(r_ramp² - (x - arc_cx)²)
# Derivative: dy/dx = -(x - arc_cx) / sqrt(r_ramp² - (x - arc_cx)²)
# angle = round(-atan2(dy/dx, 1) * 256 / (2*pi)) % 256
```

Or simpler: evaluate sy at x and x+1, compute delta, use atan2.

## Constraints and Risks

1. **Floating-point at boundaries**: At x = arc_cx ± r_ramp, `val = r_ramp² - dx²` may go slightly negative. Need `max(0, val)` guard.
2. **Tile overlap at tangent points**: Entry ramp ends at `cx - r`, loop starts at `cx - r`. The ramp is placed BEFORE loop tiles, so loop tiles overwrite at the junction — same pattern as svg2stage.
3. **`_build_segment_map` consistency**: Must use the updated `seg.len` that includes ramps.
4. **`r_ramp` default**: Ticket says `r_ramp` defaults to the loop radius. For now, hardcode `r_ramp = radius`.
