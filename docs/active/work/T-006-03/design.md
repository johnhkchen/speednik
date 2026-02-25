# T-006-03 Design: profile2stage-loop-segment

## Decision Summary

Extend `profile2stage.py` with an analytical circle rasterizer that iterates every
integer pixel column in the circle's x-range, computes exact y-intersections via
`sqrt(r² - dx²)`, and uses `math.ceil` for height. Transition arcs use the same
analytical approach with a quarter-circle of configurable radius.

## Option A: Port svg2stage's sample-based loop rasterizer

Copy `_rasterize_loop` from svg2stage.py which walks pre-sampled line segments of
the ellipse perimeter.

**Pros:** Known working code, minimal design effort.
**Cons:** Sample-based approach is exactly what caused the 1px gap bugs in T-006-01.
The whole point of T-006-03 is to use analytical per-pixel-column math from the start.
Would need the same ceil fix and might still miss columns between samples.

**Rejected:** Contradicts the ticket's core requirement for analytical rasterization.

## Option B: Analytical per-pixel-column circle rasterizer (CHOSEN)

For each integer pixel column `px` in `[cx-r, cx+r)`:
1. `dx = px - cx + 0.5` (pixel center)
2. `dy = sqrt(r² - dx²)` if `|dx| <= r`, else skip
3. Bottom arc: `y_bottom = cy + dy`, Top arc: `y_top = cy - dy`
4. Rasterize both points using a loop-aware `_set_loop_pixel` method

**Pros:**
- Every pixel column is visited exactly once — zero gap risk
- `math.ceil` height rounding from T-006-01 applies naturally
- Tangent angle computed analytically per column (no segment approximation)
- Clean separation: bottom arc (FULL solidity), top arc (TOP_ONLY)

**Cons:** New code (not a port), needs thorough testing.

**Chosen** because it directly implements the ticket's specification and eliminates
the class of bugs that T-006-01 fixed retroactively.

## Option C: Parametric arc sampling at 1px arc-length intervals

Walk the circle parametrically at `dθ` intervals ensuring ≤1px arc-length steps.

**Pros:** More natural for non-circular arcs.
**Cons:** Still sample-based (columns can be skipped if arc-length step doesn't align
with pixel grid). Over-engineered for a perfect circle where the x-column iteration
is simpler and gap-free.

**Rejected:** Column-iteration (Option B) is simpler and provably complete.

## Detailed Design

### 1. SegmentDef Extension

Add `radius: int = 0` field to `SegmentDef`. For loop segments:
- `seg = "loop"`, `radius > 0`, `len` is unused (set to `2 * radius` internally).
- Parser validates: error if `radius < 32`, warning if `radius < 64`.
- `len` field becomes optional in parser for loop segments (not required).

### 2. Synthesizer._rasterize_loop(seg)

```
cx = cursor_x + radius
cy = cursor_y - radius

for px in range(cursor_x, cursor_x + 2*radius):
    dx = px - cx + 0.5
    if abs(dx) > radius: continue
    dy = sqrt(radius² - dx²)

    # Bottom arc (floor of loop interior)
    y_bottom = cy + dy
    _set_loop_pixel(px, y_bottom, angle_bottom, is_upper=False)

    # Top arc (ceiling of loop interior)
    y_top = cy - dy
    _set_loop_pixel(px, y_top, angle_top, is_upper=True)

# Ground fill under the loop (below cursor_y)
_fill_below(cursor_x, cursor_x + 2*radius)

cursor_x += 2 * radius
# cursor_y unchanged (loop exits at same height as entry)
# cursor_slope unchanged (tangent at exit = tangent at entry for full circle)
```

### 3. _set_loop_pixel(col, y, angle, is_upper)

Similar to `_set_surface_pixel` but:
- Sets `surface_type = SURFACE_LOOP` instead of `SURFACE_SOLID`
- Sets `is_loop_upper = is_upper`
- Uses `math.ceil(tile_bottom - y)` for height (matching T-006-01 fix)

### 4. Angle Computation

For pixel column `px` on the circle `(cx, cy, r)`:
- `dx = px - cx + 0.5`
- `dy = sqrt(r² - dx²)`
- Bottom arc tangent (CW traversal, rightward at bottom): `(-dy/r, dx/r)` normalized
  - Actually: at point `(cx+dx, cy+dy)`, outward radius direction is `(dx, dy)/r`.
    Tangent perpendicular (CW for rightward traversal on bottom) is `(-dy, dx)/r`.
    Byte angle: `round(-atan2(dx/r, -(-dy/r)) * 256/(2π)) % 256`
    Simplified: `round(-atan2(dx, dy) * 256/(2π)) % 256`
- Top arc tangent (CW traversal, leftward at top): tangent is `(dy, -dx)/r`.
    Byte angle: `round(-atan2(-dx, -dy) * 256/(2π)) % 256`

### 5. Transition Arcs

For MVP, transition arcs use a quarter-circle with radius `t_r = min(radius, 64)`:

**Entry arc** (flat → vertical):
- Arc center: `(cursor_x, cursor_y - t_r)`
- Sweeps from 6 o'clock (bottom, horizontal tangent) to 9 o'clock (left, vertical tangent)
- For each px in `[cursor_x - t_r, cursor_x)`:
  - `dx = px - (cursor_x - t_r) + 0.5` ... actually iterate the quarter circle columns
- Rasterized as SURFACE_SOLID (not SURFACE_LOOP — it's a transition, not part of the loop)
- Advances cursor_x backward by t_r (the arc is placed before the loop)

Wait — the entry arc should be placed BEFORE the loop circle, bridging from the current
cursor position to the loop entry point. The entry point of the loop is at
`(cursor_x, cursor_y)` after the transition arc is complete. So:

**Revised approach:** Insert transition arcs that adjust the cursor position before and
after the main loop circle. The transition arc's footprint is added to the total advance.

- Entry transition: quarter-circle rising from `cursor_y` to `cursor_y - t_r`,
  horizontal extent = `t_r`. The cursor advances by `t_r` and cursor_y decreases by `t_r`.
- But then the loop expects `cursor_y` to be at ground level (bottom of circle).

**Simplification for MVP:** The ticket says the transition arcs bridge slope differences.
For flat → loop, the most natural transition is to NOT insert separate arcs but instead
let the loop's own bottom arc serve as the transition. The player runs along the flat
ground, hits the loop's bottom arc, and the circle geometry naturally curves upward.

The ticket explicitly says "insert a transition arc at the loop entry and exit" but
also notes this is a short quarter-circle proportional to slope difference. For flat
approach (slope=0 → vertical), this is the maximum case.

**Decision:** Implement transition arcs as quarter-circle SOLID segments that precede
and follow the main loop circle. Horizontal footprint = `t_r` each side. Total cursor
advance = `2*t_r + 2*radius`. The transition arc raises/lowers the surface from
`cursor_y` to the loop's side entry/exit height. For the first implementation, use
`t_r = radius // 4` (small relative to loop) to keep the transition short.

If `cursor_slope != 0` (ramp into loop), `t_r` is reduced proportionally:
`t_r = int(radius // 4 * (1 - min(abs(cursor_slope), 1)))`.

### 6. Ground Fill

After the loop circle (and transition arcs), call `_fill_below` spanning the entire
footprint `[original_cursor_x, original_cursor_x + total_advance)`. This fills the
ground under the loop (below `cursor_y`) as solid, ensuring the player can stand
beneath the loop.

The key: `_fill_below` fills below the TOPMOST tile in each column. For columns inside
the loop, the topmost tile is the top arc. Fill below would flood the interior. So
`_fill_below` must be called ONLY for columns where the topmost surface tile is at or
below `cursor_y` — i.e., not through the loop circle columns.

**Better approach:** Don't call `_fill_below` for loop columns at all. Instead, explicitly
fill ground tiles in the range `[cursor_x, cursor_x + 2*radius)` for rows below `cursor_y`
only. This is a separate `_fill_ground_under_loop` method.

### 7. VALID_SEG_TYPES Update

Change from `{"flat", "ramp", "gap"}` to `{"flat", "ramp", "gap", "loop"}`.

### 8. Import Update

Add `SURFACE_LOOP` to the import list from svg2stage.

## Testing Strategy

1. **No-gap test:** Create loop with flat approach, run Validator, assert zero "Impassable gap" errors.
2. **Hollow interior:** Sample tiles at `(cx//16, cy//16)` — should be None (empty interior).
3. **Solidity flags:** Check upper arc tiles have `is_loop_upper=True`, lower have `False`.
4. **Cursor advance:** After loop, `cursor_x == original + 2*radius + 2*t_r`.
5. **Radius validation:** `radius < 32` raises, `radius < 64` warns.
6. **Update existing test:** `test_invalid_seg_type_raises` currently expects "loop" to fail.
   Change to test a truly invalid type like "teleport".
