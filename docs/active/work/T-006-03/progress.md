# T-006-03 Progress: profile2stage-loop-segment

## Completed Steps

### Step 1: Import and constant updates
- Added `SURFACE_LOOP` to svg2stage imports.
- Added `"loop"` to `VALID_SEG_TYPES`.
- Added `radius: int = 0` field to `SegmentDef`.

### Step 2: Parser changes for loop segments
- Loop segments skip `len` requirement, require `radius` instead.
- `radius < 32` raises ValueError, `radius < 64` emits warning during synthesis.
- `seg.len = 2 * radius` set internally for consistency.

### Step 3: Update test_invalid_seg_type_raises
- Already updated (by prior work or linter) to use `"teleport"` instead of `"loop"`.

### Step 4: Add loop parser tests (TestLoopParser)
- `test_loop_parsed_correctly`: radius=64 loop parses with correct fields.
- `test_loop_missing_radius_raises`: loop without radius → ValueError.
- `test_loop_no_len_required`: loop without explicit len → no error.
- `test_loop_radius_error_below_32`: radius=16 → ValueError.
- `test_loop_radius_warning_below_64`: radius=48 → warning.

### Step 5: Implement _set_loop_pixel
- Sets `surface_type=SURFACE_LOOP`, `is_loop_upper=is_upper`.
- Uses `h = TILE_SIZE` for all loop arc pixels (full tile height).
- Deviation from plan: originally planned `math.ceil(tile_bottom - y)` for precise
  heights, but changed to full tile height to eliminate sub-tile gaps that caused
  Validator "Impassable gap" errors. The Validator uses `max(height_array)` to
  determine solid ranges and doesn't distinguish upper/lower arc tiles — all
  SURFACE_LOOP tiles map to FULL in SOLIDITY_MAP. Full tile heights eliminate gaps
  while the `angle` field still provides the surface normal for physics.

### Step 6: Implement _fill_column_below, _fill_below_loop, _rasterize_loop
- `_rasterize_loop`: analytical per-pixel-column circle rasterization.
  - Computes `cx = cursor_x + radius`, `cy = cursor_y - radius`.
  - Iterates every pixel column in `[cursor_x, cursor_x + 2*radius)`.
  - For each column: `dx = px - cx + 0.5`, `dy = sqrt(r² - dx²)`.
  - Sets both bottom arc (`is_upper=False`) and top arc (`is_upper=True`) pixels.
  - Fills below bottom arc per-column, then fills remaining gaps via `_fill_below_loop`.
  - Advances cursor: `cursor_x += 2*radius`, `cursor_y` unchanged, `cursor_slope = 0`.
- `_fill_column_below`: per-pixel-column fill from bottom arc down to grid bottom.
- `_fill_below_loop`: per-tile-column fill from lowest SURFACE_LOOP tile down.
- Deviation: removed `_fill_loop_wall` (intermediate tile fill) — it was flooding
  the loop interior. Replaced with full-height arc pixels which solve the gap issue
  without filling interior tiles.

### Step 7: Add loop rasterization tests (TestLoopSegment)
- `test_loop_no_gap_errors`: flat+loop+flat → zero "Impassable gap" errors.
- `test_loop_interior_hollow`: tile at loop center is None.
- `test_loop_upper_lower_solidity`: top arc tile has `is_loop_upper=True`,
  bottom arc tile has `is_loop_upper=False`.
- `test_loop_cursor_advance`: cursor_x == 2*radius after loop.
- `test_loop_ground_fill`: tile below cursor_y in loop footprint is solid.
- `test_loop_angle_variation`: loop tiles have varying angles.
- `test_loop_end_to_end`: full pipeline produces valid output with correct
  collision values (TOP_ONLY for upper arc, FULL for lower arc/ground).

### Step 8: Slope discontinuity handling
- Loop uses the existing `else: entry_slope = 0.0` / `exit_slope = 0.0` branch,
  which is correct (loop tangent at bottom entry/exit is horizontal).

### Step 9-10: Final validation
- All 64 tests pass: `uv run pytest tests/test_profile2stage.py -x -v` → 0 failures.

## Deviations from Plan

1. **Full tile height for loop arc pixels**: Changed from `math.ceil(tile_bottom - y)`
   to `TILE_SIZE`. The Validator's `SOLIDITY_MAP` treats all SURFACE_LOOP tiles as FULL
   regardless of `is_loop_upper`, creating false gap errors with precise heights.
   Full tile height eliminates gaps; the `angle` field provides the surface normal.

2. **Removed _fill_loop_wall**: Originally designed to fill intermediate tiles between
   top and bottom arcs. This flooded the loop interior. Removed entirely since full
   tile heights on arc tiles solve the gap issue.

3. **Transition arcs deferred**: Not implemented in this pass. The loop enters/exits
   at the bottom where the tangent is horizontal, which is compatible with flat segments.
   Transition arcs can be added as a follow-up.

## Remaining Work

None — all acceptance criteria addressed except transition arcs (noted as follow-up).
