# T-007-03 Design: profile2stage Loop Entry/Exit Ramps

## Problem

`_rasterize_loop` generates a bare circle with no transition geometry. The player hits an angle discontinuity from 0° (flat ground) to ~64° (loop tangent) at the loop boundary, and from ~192° back to 0° at the exit.

## Approaches Considered

### A: Inline ramp generation in `_rasterize_loop` (Chosen)

Add entry/exit ramp pixel loops directly inside `_rasterize_loop`, before and after the existing circle rasterization. Use the same quarter-circle arc equation as svg2stage but adapted to profile2stage's existing helpers (`_set_surface_pixel`, `_fill_below`).

**Pros:**
- Self-contained: all loop-related rasterization in one method
- Reuses existing `_set_surface_pixel` for tile placement (consistent with flat/ramp/wave)
- Reuses existing `_fill_below` for ground fill (no new fill logic)
- Angle computation uses the same inline atan2 pattern as other segments

**Cons:**
- Makes `_rasterize_loop` longer (~50 additional lines)

### B: Separate `_rasterize_loop_ramps` method

Extract ramp logic into its own method, called from `_rasterize_loop`.

**Pros:**
- Cleaner separation of concerns
- Method stays shorter

**Cons:**
- Adds indirection for logic that's only used in one place
- Requires passing cx, cy, radius, r_ramp, ground_y — lots of params

**Rejected:** Over-abstraction for a single call site. The ramp logic is tightly coupled to loop geometry and doesn't warrant its own method.

### C: Pre/post segment approach (synthetic ramp segments)

Insert synthetic "loop_entry_ramp" and "loop_exit_ramp" segments before and after the loop in the segment list during parsing.

**Pros:**
- Each segment type handles itself
- Clean separation

**Cons:**
- Violates the user's segment model (they define "loop", not "ramp + loop + ramp")
- Complicates segment map, entity resolution, and segment ID tracking
- Parsing should not synthesize new segments

**Rejected:** Breaks the declarative profile model.

## Decision: Approach A — Inline in `_rasterize_loop`

### Arc Geometry

Entry ramp (left side):
- Arc center: `(loop_left_x, cy)` where `loop_left_x = cx - radius` and `cx = cursor_x + r_ramp + radius`
- X range: `[cursor_x, cursor_x + r_ramp)`
- Surface: `sy = cy + sqrt(r_ramp² - (px - loop_left_x)²)`
- Ground level check: `sy = min(sy, ground_y)` where `ground_y = cursor_y`

Exit ramp (right side):
- Arc center: `(loop_right_x, cy)` where `loop_right_x = cx + radius`
- X range: `(cursor_x + r_ramp + 2*radius, cursor_x + r_ramp + 2*radius + r_ramp]`
- Same surface equation, mirrored

### Angle Computation

Use finite-difference from consecutive arc points:
```python
sy0 = arc_surface_y(px)
sy1 = arc_surface_y(px + 1)
slope = sy1 - sy0  # dy/dx over 1 pixel
angle = round(-math.atan2(slope, 1.0) * 256 / (2 * math.pi)) % 256
```

This is consistent with how svg2stage does it and avoids the analytical derivative (which requires special handling at the arc boundary where the denominator goes to zero).

### Tile Properties

Ramp tiles:
- `surface_type = SURFACE_SOLID`
- No `is_loop_upper` flag
- Height arrays via `_set_surface_pixel` (same as flat/ramp segments)
- Ground fill via `_fill_below` covering the full ramp + loop + ramp extent

### Cursor Updates

Before: `cursor_x += 2 * radius`
After: `cursor_x += r_ramp + 2 * radius + r_ramp` (= `4 * radius` when r_ramp = radius)

`cursor_y` unchanged (loop exits at entry height). `cursor_slope` = 0.0 (exit ramp returns to flat).

### Segment Length Update

`seg.len` is set to `2 * radius` during parsing. It needs to become `2 * r_ramp + 2 * radius` to keep `_build_segment_map` consistent. Since `r_ramp = radius`, this is `4 * radius`.

**Where to change:** In `ProfileParser.load()` at line 135: `seg_len = 2 * radius + 2 * radius` → `seg_len = 4 * radius`.

This is the cleanest approach because all downstream code (segment map, entity offset resolution, width validation) uses `seg.len` and will automatically be correct.

### Ordering: Ramps Before Circle

Entry ramp is rasterized first, then the circle, then the exit ramp. If any ramp pixel overlaps with a loop circle pixel at the tangent point, the loop pixel overwrites it — which is correct because the tangent point belongs to the loop, not the ramp.

Actually, in profile2stage the circle is rasterized per-column analytically, so there's no true overlap at the tangent column. But placing ramps first is still the safe ordering.

### Ground Fill Strategy

Call `_fill_below(full_start, full_end)` after the exit ramp where the range covers the entire ramp + loop + ramp footprint. This fills below all surface tiles (ramp SURFACE_SOLID and below-loop SURFACE_SOLID fill tiles) uniformly. The existing `_fill_below_loop` call handles the loop-specific fill.

Simplification: the existing `_fill_below_loop` only fills below SURFACE_LOOP tiles. The ramp tiles are SURFACE_SOLID and handled by `_fill_below`. So we call both:
1. `_fill_below_loop(loop_start, loop_end)` — fills below loop circle
2. `_fill_below(ramp_entry_start, ramp_exit_end)` — fills below everything including ramps

`_fill_below` finds the topmost tile per column and fills below. For ramp columns, the topmost tile is the ramp surface. For loop columns, it's the top-arc loop tile (which we don't want to fill below — we want hollow interior). But `_fill_below` would fill below the topmost tile in loop columns too, flooding the interior.

**Fix:** Don't use `_fill_below` for the full range. Instead:
1. `_fill_below(entry_start, entry_end)` — fills below entry ramp only
2. Circle rasterization (existing `_fill_column_below` + `_fill_below_loop`)
3. `_fill_below(exit_start, exit_end)` — fills below exit ramp only

This keeps ramp fill and loop fill separate, preserving the hollow interior.

### Test Updates

Existing tests need center coordinate adjustments because the loop circle now starts at `cursor_x + r_ramp` instead of `cursor_x`. The helper `_make_loop_profile` width calculation changes from `flat_before + 2*radius + flat_after` to `flat_before + 4*radius + flat_after`.

New tests:
1. Ramp tiles exist before and after the loop circle
2. Ramp tile angles progress smoothly from ~0° to loop tangent
3. Ramp tiles are SURFACE_SOLID with FULL solidity
4. Cursor advances by 4*radius
5. No gaps at ramp-to-loop junctions
