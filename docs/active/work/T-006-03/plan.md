# T-006-03 Plan: profile2stage-loop-segment

## Step 1: Import and constant updates

**Files:** `tools/profile2stage.py`

- Add `SURFACE_LOOP` to the import from `svg2stage`.
- Add `"loop"` to `VALID_SEG_TYPES`.
- Add `radius: int = 0` field to `SegmentDef`.

**Verify:** File still imports cleanly (`python -c "import profile2stage"`).

## Step 2: Parser changes for loop segments

**Files:** `tools/profile2stage.py` (ProfileParser.load)

- For `seg == "loop"`: skip `len` requirement, require `radius` field instead.
- Validate `radius` is a positive int ≥ 32. Error if < 32, store warning if < 64.
- Set `seg.len = 2 * radius` internally.
- For loop segments, `len` is not required in the JSON input.

**Verify:** Manual test — load a profile JSON with a loop segment, confirm parsing succeeds.

## Step 3: Update test_invalid_seg_type_raises

**Files:** `tests/test_profile2stage.py`

- Change the test's segment type from `"loop"` to `"teleport"`.
- Run: `uv run pytest tests/test_profile2stage.py::TestProfileParser::test_invalid_seg_type_raises -x`

**Verify:** Test passes. No regressions in other parser tests.

## Step 4: Add loop parser tests

**Files:** `tests/test_profile2stage.py`

- Add `TestLoopParser` class:
  - `test_loop_parsed_correctly`: radius=64 loop segment parses.
  - `test_loop_missing_radius_raises`: loop without radius → ValueError.
  - `test_loop_no_len_required`: loop without explicit len → no error.
  - `test_loop_radius_error_below_32`: radius=16 → ValueError.
  - `test_loop_radius_warning_below_64`: radius=48 → warning in output.

**Verify:** `uv run pytest tests/test_profile2stage.py::TestLoopParser -x` — all pass.

## Step 5: Implement _set_loop_pixel

**Files:** `tools/profile2stage.py`

- New method on `Synthesizer`:
  ```
  def _set_loop_pixel(self, col, y, angle, is_upper):
      tx = col // TILE_SIZE
      local_x = col % TILE_SIZE
      ty = int(y) // TILE_SIZE
      if out of bounds: return
      tile_bottom = (ty + 1) * TILE_SIZE
      h = max(0, min(TILE_SIZE, math.ceil(tile_bottom - y)))
      # Create or update tile with SURFACE_LOOP
      tile.is_loop_upper = is_upper (or existing | is_upper)
  ```

**Verify:** Unit-level — will be exercised by _rasterize_loop tests in step 7.

## Step 6: Implement _fill_ground_under_loop and _rasterize_loop

**Files:** `tools/profile2stage.py`

- `_fill_ground_under_loop(start_col, end_col, ground_y)`:
  - Compute tile row for `ground_y`.
  - For each tile column in range: fill from ground row down with SURFACE_SOLID solid tiles.
  - Skip if tile already exists (don't overwrite loop tiles).

- `_rasterize_loop(seg)`:
  - Compute `cx`, `cy` from cursor position and radius.
  - For each pixel column `px` in `[cursor_x, cursor_x + 2*radius)`:
    - `dx = px - cx + 0.5`, skip if `|dx| > radius`.
    - `dy = sqrt(radius² - dx²)`.
    - Bottom arc: `y = cy + dy`, compute angle, call `_set_loop_pixel(..., is_upper=False)`.
    - Top arc: `y = cy - dy`, compute angle, call `_set_loop_pixel(..., is_upper=True)`.
  - Call `_fill_ground_under_loop(cursor_x, cursor_x + 2*radius, cursor_y)`.
  - Advance cursor: `cursor_x += 2 * radius`, cursor_y unchanged, cursor_slope = 0.

- Add dispatch in `synthesize()`: `elif seg.seg == "loop": self._rasterize_loop(seg)`.

**Verify:** `uv run pytest tests/test_profile2stage.py -x` — no regressions.

## Step 7: Add loop rasterization tests

**Files:** `tests/test_profile2stage.py`

- Add `TestLoopSegment` class:
  - `test_loop_no_gap_errors`: flat(128) + loop(r=64) + flat(128), width=512, height=720.
    Synthesize → Validator → assert no "Impassable gap" in issues.
  - `test_loop_interior_hollow`: radius=64 loop. Check tile at `(cx//16, cy//16)` is None.
  - `test_loop_upper_lower_solidity`: Check top-arc tile has `is_loop_upper=True`,
    bottom-arc tile has `is_loop_upper=False`.
  - `test_loop_cursor_advance`: After loop, `cursor_x == start + 2*radius`.
  - `test_loop_ground_fill`: Tile below `cursor_y` in loop footprint is solid SURFACE_SOLID.
  - `test_loop_angle_variation`: Angles on loop tiles are not all the same.

**Verify:** `uv run pytest tests/test_profile2stage.py::TestLoopSegment -x` — all pass.

## Step 8: Slope discontinuity handling for loops

**Files:** `tools/profile2stage.py`

- In `_check_slope_discontinuities`: add `elif seg.seg == "loop":` with entry_slope=0,
  exit_slope=0 (loop enters/exits at bottom where tangent is horizontal).

**Verify:** Full test suite passes. No false discontinuity warnings for flat → loop → flat.

## Step 9: Integration test with full pipeline

**Files:** `tests/test_profile2stage.py`

- Add `test_loop_end_to_end`: Full pipeline (parse → synthesize → validate → write).
  Verify all 5 output files created. Verify collision.json has TOP_ONLY (1) for upper
  arc tiles and FULL (2) for lower arc tiles.

**Verify:** `uv run pytest tests/test_profile2stage.py -x` — entire suite passes.

## Step 10: Final validation

- Run: `uv run pytest tests/test_profile2stage.py -x -v`
- Confirm zero failures, zero errors.
- Review any validation warnings in test output.

## Testing Strategy

| Test | Type | What it verifies |
|------|------|-----------------|
| test_loop_parsed_correctly | Unit | Parser accepts loop segments |
| test_loop_missing_radius_raises | Unit | Parser rejects loop without radius |
| test_loop_no_len_required | Unit | Parser doesn't require len for loops |
| test_loop_radius_error_below_32 | Unit | Parser rejects radius < 32 |
| test_loop_radius_warning_below_64 | Unit | Parser warns on radius < 64 |
| test_loop_no_gap_errors | Integration | Analytical rasterization has no gaps |
| test_loop_interior_hollow | Integration | Interior is not filled |
| test_loop_upper_lower_solidity | Unit | is_loop_upper flag set correctly |
| test_loop_cursor_advance | Unit | Cursor position correct after loop |
| test_loop_ground_fill | Unit | Ground below cursor_y is solid |
| test_loop_angle_variation | Unit | Per-column tangent angles computed |
| test_loop_end_to_end | E2E | Full pipeline produces correct output |
| test_invalid_seg_type_raises | Regression | Updated to use "teleport" |

## Commit Strategy

Single atomic commit containing all changes to both files. The loop feature is
self-contained and all tests must pass together.
