# T-007-03 Structure: profile2stage Loop Entry/Exit Ramps

## Files Modified

### 1. `tools/profile2stage.py`

#### ProfileParser.load() — line 135
- Change: `seg_len = 2 * radius` → `seg_len = 4 * radius`
- Reason: Loop segment footprint now includes entry ramp (radius) + circle (2*radius) + exit ramp (radius)

#### Synthesizer._rasterize_loop() — lines 627–672
- Substantial modification. New structure:

```
def _rasterize_loop(self, seg: SegmentDef) -> list[str]:
    # 1. Setup (unchanged): warnings, radius, r_ramp = radius
    # 2. Compute geometry:
    #    - entry_start = cursor_x
    #    - loop_start  = cursor_x + r_ramp
    #    - loop_end    = cursor_x + r_ramp + 2*radius
    #    - exit_end    = cursor_x + r_ramp + 2*radius + r_ramp
    #    - cx = loop_start + radius  (circle center x)
    #    - cy = cursor_y - radius    (circle center y)
    #    - ground_y = cursor_y       (same as cy + radius)
    #
    # 3. Entry ramp: quarter-circle arc
    #    - Arc center: (loop_start, cy) = leftmost point of loop circle
    #    - For px in [entry_start, loop_start):
    #      - sy = cy + sqrt(r_ramp² - (px - loop_start)²)
    #      - Clamp sy to ground_y
    #      - Compute angle from finite difference
    #      - _set_surface_pixel(px, sy, angle)
    #    - _fill_below(entry_start, loop_start)
    #
    # 4. Loop circle (existing logic, adjusted coordinates):
    #    - start_col = loop_start, end_col = loop_end
    #    - cx = loop_start + radius (shifted by r_ramp from old calculation)
    #    - Same per-column arc math: bottom arc, top arc, fill below
    #
    # 5. Exit ramp: quarter-circle arc (mirrored)
    #    - Arc center: (loop_end, cy) = rightmost point of loop circle
    #    - For px in (loop_end, exit_end]:
    #      - sy = cy + sqrt(r_ramp² - (px - loop_end)²)
    #      - Clamp sy to ground_y
    #      - Compute angle from finite difference
    #      - _set_surface_pixel(px, sy, angle)
    #    - _fill_below(loop_end, exit_end)
    #
    # 6. Cursor advance:
    #    - cursor_x = exit_end  (= old cursor_x + 4*radius)
    #    - cursor_y unchanged
    #    - cursor_slope = 0.0
```

#### Helper: `_arc_surface_y` (local function inside _rasterize_loop)
- Input: px (int), arc_cx (float), r_ramp (float), cy (float)
- Output: float — surface y on the quarter-circle arc
- Equation: `cy + sqrt(max(0, r_ramp² - (px - arc_cx)²))`
- Used by both entry and exit ramp loops

#### Helper: `_ramp_angle` (local function inside _rasterize_loop)
- Input: px (int), arc_cx, r_ramp, cy
- Output: int — byte angle (0–255)
- Method: finite difference between arc_surface_y(px) and arc_surface_y(px+1)
- Formula: `round(-atan2(sy1 - sy0, 1.0) * 256 / (2*pi)) % 256`

### 2. `tests/test_profile2stage.py`

#### Existing test updates (TestLoopSegment class):

**`_make_loop_profile` helper (line 1031)**
- Change `total = flat_before + 2 * radius + flat_after` → `total = flat_before + 4 * radius + flat_after`
- Reason: segment footprint now includes ramps

**`test_loop_interior_hollow` (line 1058)**
- Change center calculation: `cx = 128 + radius` → `cx = 128 + 2 * radius`
- The entry ramp shifts the circle right by r_ramp = radius

**`test_loop_upper_lower_solidity` (line 1077)**
- Same center shift: `cx = 128 + radius` → `cx = 128 + 2 * radius`
- cy calculation: `400 - radius` unchanged

**`test_loop_cursor_advance` (line 1119)**
- Change: `assert synth.cursor_x == 2 * radius` → `assert synth.cursor_x == 4 * radius`
- Also update width to accommodate: width must be >= 4*radius

**`test_loop_ground_fill` (line 1135)**
- Update center tile calculation for shifted loop position

**`test_loop_angle_variation` (line 1153)**
- No change needed (still checks for varying angles on SURFACE_LOOP tiles)

**`test_loop_no_gap_errors` (line 1047)**
- May need width increase; otherwise should pass

**`test_loop_end_to_end` (line 1171)**
- Width 512 should accommodate 128 + 4*64 + 128 = 512 (exactly fits)

#### New tests:

**`test_loop_ramp_tiles_exist`**
- Verify SURFACE_SOLID tiles exist in the entry ramp region [flat_before, flat_before + radius)
- Verify SURFACE_SOLID tiles exist in the exit ramp region [flat_before + 3*radius, flat_before + 4*radius)

**`test_loop_ramp_angles_progress`**
- Sample ramp tile angles across the entry ramp
- Verify they are not all the same (progress from ~0° toward loop tangent)

**`test_loop_ramp_no_gaps_at_junction`**
- Check the tile column at the ramp-to-loop boundary (loop_start)
- Verify no empty tiles between the last ramp tile and the first loop tile

**`test_loop_ramp_surface_type`**
- Verify all ramp tiles have surface_type == SURFACE_SOLID
- Verify none have is_loop_upper set

**`test_loop_cursor_includes_ramps`**
- Loop-only segment: cursor_x should be 4*radius
- cursor_y unchanged, cursor_slope = 0.0

## Files NOT Modified

- `tools/svg2stage.py` — no changes, reference only
- `speednik/` game code — no changes
- `docs/active/tickets/T-007-03.md` — frontmatter managed by Lisa

## Module Boundaries

- All changes are within `tools/profile2stage.py` and `tests/test_profile2stage.py`
- No new imports needed (math already imported)
- No new public API (local helper functions only)
- No changes to shared svg2stage components
